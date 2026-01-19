from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.utils import canonical_customer_key
from app.eqms.modules.customer_profiles.service import find_or_create_customer
from app.eqms.modules.rep_traceability.service import create_distribution_entry
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun
from app.eqms.modules.shipstation_sync.parsers import canonicalize_sku, extract_lot, infer_units, load_lot_log, normalize_lot
from app.eqms.modules.shipstation_sync.shipstation_client import ShipStationClient, ShipStationError


def _safe_text(v: Any) -> str:
    try:
        return (v or "").strip()
    except Exception:
        return ""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    # ShipStation expects ISO-ish; legacy used fractional seconds.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-1] + "0"


def _build_external_key(*, shipment_id: str, sku: str, lot_number: str) -> str:
    return f"{shipment_id}:{sku}:{lot_number}"


def _get_customer_from_ship_to(s, ship_to: dict[str, Any]) -> Customer | None:
    facility = _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name"))
    if not facility:
        return None
    ck = canonical_customer_key(facility)
    if not ck:
        return None
    existing = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
    if existing:
        return existing
    return find_or_create_customer(
        s,
        facility_name=facility,
        address1=_safe_text(ship_to.get("street1") or ship_to.get("address1")),
        address2=_safe_text(ship_to.get("street2") or ship_to.get("address2")),
        city=_safe_text(ship_to.get("city")),
        state=_safe_text(ship_to.get("state") or ship_to.get("stateCode")),
        zip=_safe_text(ship_to.get("postalCode") or ship_to.get("postal")),
    )


def run_sync(s, *, user: User) -> ShipStationSyncRun:
    """
    Lean ShipStation sync:
    - Admin-triggered (sync request thread)
    - Idempotent per shipment+sku+lot (distribution_log_entries.external_key)
    - No background jobs
    """
    api_key = (os.environ.get("SHIPSTATION_API_KEY") or "").strip()
    api_secret = (os.environ.get("SHIPSTATION_API_SECRET") or "").strip()
    if not api_key or not api_secret:
        raise ValueError("SHIPSTATION_API_KEY and SHIPSTATION_API_SECRET are required.")

    days = int((os.environ.get("SHIPSTATION_DEFAULT_DAYS") or "30").strip() or "30")
    lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()

    client = ShipStationClient(api_key=api_key, api_secret=api_secret)
    lot_to_sku, lot_corrections = load_lot_log(lotlog_path)

    start = time.time()
    now = _now_utc()
    start_dt = now - timedelta(days=days)

    record_event(
        s,
        actor=user,
        action="shipstation.sync_started",
        entity_type="ShipStationSync",
        entity_id=None,
        metadata={"days": days},
    )

    orders_seen = 0
    shipments_seen = 0
    synced = 0
    skipped = 0

    try:
        # Orders list (pagination)
        for page in range(1, 51):
            orders = client.list_orders(create_date_start=_iso_utc(start_dt), create_date_end=_iso_utc(now), page=page, page_size=100)
            if not orders:
                break

            for o in orders:
                orders_seen += 1
                order_id = str(o.get("orderId") or "")
                order_number = _safe_text(o.get("orderNumber"))
                if not order_id or not order_number:
                    skipped += 1
                    s.add(
                        ShipStationSkippedOrder(
                            order_id=order_id or None,
                            order_number=order_number or None,
                            reason="missing_order_id_or_number",
                            details_json=json.dumps({"order": o}, default=str)[:4000],
                        )
                    )
                    continue

                # Order details (shipTo + items + internal notes)
                det = client.get_order(order_id)
                ship_to = det.get("shipTo") if isinstance(det.get("shipTo"), dict) else {}
                internal_notes = _safe_text(det.get("internalNotes"))
                items = det.get("items") if isinstance(det.get("items"), list) else []

                # Shipments (pagination)
                shipments: list[dict[str, Any]] = []
                for spage in range(1, 11):
                    chunk = client.list_shipments_for_order(order_id, page=spage, page_size=100)
                    if not chunk:
                        break
                    shipments.extend([x for x in chunk if isinstance(x, dict)])
                    if len(chunk) < 100:
                        break
                shipments_seen += len(shipments)

                if not shipments:
                    skipped += 1
                    s.add(
                        ShipStationSkippedOrder(
                            order_id=order_id,
                            order_number=order_number,
                            reason="no_shipments",
                            details_json=json.dumps({"order_id": order_id, "order_number": order_number}, default=str),
                        )
                    )
                    continue

                # Build sku -> units map
                sku_units: dict[str, int] = {}
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    sku = canonicalize_sku(_safe_text(it.get("sku")) or _safe_text(it.get("name")))
                    if not sku:
                        continue
                    qty = infer_units(_safe_text(it.get("name")), int(it.get("quantity") or 0))
                    if qty <= 0:
                        continue
                    sku_units[sku] = sku_units.get(sku, 0) + qty

                if not sku_units:
                    skipped += 1
                    s.add(
                        ShipStationSkippedOrder(
                            order_id=order_id,
                            order_number=order_number,
                            reason="no_valid_items",
                            details_json=json.dumps({"items": items}, default=str)[:4000],
                        )
                    )
                    continue

                customer = _get_customer_from_ship_to(s, ship_to)
                facility_name = _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name")) or (customer.facility_name if customer else "UNKNOWN")

                # One lot per order (lean). Try notes, then lotlog lookup.
                raw_lot = extract_lot(internal_notes)
                lot = normalize_lot(raw_lot) if raw_lot else "UNKNOWN"
                
                # Apply LotLog corrections if available (e.g., SLQ-050220 -> SLQ-05022025)
                if lot in lot_corrections:
                    lot = lot_corrections[lot]

                # Lookup SKU from LotLog using multiple key variants
                lot_key = lot[4:] if lot.startswith("SLQ-") else lot
                mapped_sku = lot_to_sku.get(lot) or lot_to_sku.get(lot_key) or lot_to_sku.get(raw_lot or "")

                for sh in shipments:
                    shipment_id = _safe_text(sh.get("shipmentId")) or _safe_text(sh.get("shipment_id"))
                    ship_date = _safe_text(sh.get("shipDate")) or _safe_text(sh.get("ship_date"))
                    tracking = _safe_text(sh.get("trackingNumber")) or _safe_text(sh.get("tracking_number"))

                    if not shipment_id:
                        continue

                    for sku, units in sku_units.items():
                        lot_for_row = lot
                        # Only set UNKNOWN if lot explicitly maps to a different SKU
                        if mapped_sku and mapped_sku != sku:
                            lot_for_row = "UNKNOWN"

                        external_key = _build_external_key(shipment_id=shipment_id, sku=sku, lot_number=lot_for_row)

                        payload = {
                            "ship_date": ship_date[:10] if ship_date else now.date().isoformat(),
                            "order_number": order_number,
                            "facility_name": facility_name,
                            "customer_id": str(customer.id) if customer else "",
                            "customer_name": customer.facility_name if customer else None,
                            "source": "shipstation",
                            "sku": sku,
                            "lot_number": lot_for_row,
                            "quantity": units,
                            "address1": _safe_text(ship_to.get("street1") or ship_to.get("address1")) or (customer.address1 if customer else None),
                            "city": _safe_text(ship_to.get("city")) or (customer.city if customer else None),
                            "state": _safe_text(ship_to.get("state") or ship_to.get("stateCode")) or (customer.state if customer else None),
                            "zip": _safe_text(ship_to.get("postalCode") or ship_to.get("postal")) or (customer.zip if customer else None),
                            "tracking_number": tracking or None,
                            "ss_shipment_id": shipment_id,
                        }

                        try:
                            # Use a SAVEPOINT so idempotent duplicates don't roll back the whole sync.
                            with s.begin_nested():
                                e = create_distribution_entry(s, payload, user=user, source_default="shipstation")
                                e.external_key = external_key
                                s.flush()  # force unique index check now
                            synced += 1
                        except IntegrityError:
                            skipped += 1
                            s.add(
                                ShipStationSkippedOrder(
                                    order_id=order_id,
                                    order_number=order_number,
                                    reason="duplicate_external_key",
                                    details_json=json.dumps({
                                        "external_key": external_key,
                                        "sku": sku,
                                        "lot": lot_for_row,
                                        "facility": facility_name[:100],
                                    }, default=str)[:4000],
                                )
                            )
                        except Exception as exc:
                            skipped += 1
                            s.add(
                                ShipStationSkippedOrder(
                                    order_id=order_id,
                                    order_number=order_number,
                                    reason="insert_failed",
                                    details_json=json.dumps({
                                        "error": str(exc),
                                        "external_key": external_key,
                                        "sku": sku,
                                        "lot": lot_for_row,
                                        "facility": facility_name[:100],
                                    }, default=str)[:4000],
                                )
                            )

        duration = int(time.time() - start)
        run = ShipStationSyncRun(
            synced_count=synced,
            skipped_count=skipped,
            orders_seen=orders_seen,
            shipments_seen=shipments_seen,
            duration_seconds=duration,
            message=f"Synced={synced} skipped={skipped}",
        )
        s.add(run)

        record_event(
            s,
            actor=user,
            action="shipstation.sync_completed",
            entity_type="ShipStationSyncRun",
            entity_id=None,
            metadata={"synced": synced, "skipped": skipped, "orders_seen": orders_seen, "shipments_seen": shipments_seen, "duration_seconds": duration},
        )
        return run
    except ShipStationError as e:
        record_event(
            s,
            actor=user,
            action="shipstation.sync_failed",
            entity_type="ShipStationSync",
            entity_id=None,
            metadata={"error": str(e)},
        )
        raise

