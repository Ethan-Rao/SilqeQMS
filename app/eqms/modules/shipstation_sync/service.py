from __future__ import annotations

import json
import os
import time
from datetime import datetime, date as date_type, timezone, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.utils import canonical_customer_key
from app.eqms.modules.customer_profiles.service import find_or_create_customer
from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
from app.eqms.modules.rep_traceability.service import create_distribution_entry
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun
from app.eqms.modules.shipstation_sync.parsers import canonicalize_sku, extract_lot, extract_sku_lot_pairs, infer_units, load_lot_log, normalize_lot
from app.eqms.modules.shipstation_sync.shipstation_client import ShipStationClient, ShipStationError


def _safe_text(v: Any) -> str:
    """Safely convert any value to stripped string."""
    if v is None:
        return ""
    try:
        return str(v).strip()
    except Exception:
        return ""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    # ShipStation expects ISO-ish; legacy used fractional seconds.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-1] + "0"


def _build_external_key(*, shipment_id: str, sku: str, lot_number: str) -> str:
    return f"{shipment_id}:{sku}:{lot_number}"


def _get_existing_customer_from_ship_to(s, ship_to: dict[str, Any]) -> Customer | None:
    """
    Look up EXISTING customer by canonical key from ship_to data.
    
    IMPORTANT: This function does NOT create new customers.
    Customers are only created from Sales Orders (PDF import, manual entry).
    ShipStation sync should only match to existing customers.
    
    If no match found, returns None (distribution will have customer_id=None
    until matched to a Sales Order that has a customer).
    """
    facility = _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name"))
    if not facility:
        return None
    ck = canonical_customer_key(facility)
    if not ck:
        return None
    # Only return EXISTING customer - never create new ones
    return s.query(Customer).filter(Customer.company_key == ck).one_or_none()


def _find_or_create_sales_order(
    s,
    *,
    order_number: str,
    order_date: date_type,
    ship_date: date_type | None,
    customer_id: int,
    source: str,
    ss_order_id: str | None = None,
    external_key: str | None = None,
    tracking_number: str | None = None,
    user: User | None = None,
) -> SalesOrder:
    """
    Find existing sales order by external_key or create new.
    Sales orders are source of truth for customer identity.
    """
    # Check if order already exists (idempotent by external_key)
    if external_key:
        existing = (
            s.query(SalesOrder)
            .filter(SalesOrder.source == source, SalesOrder.external_key == external_key)
            .one_or_none()
        )
        if existing:
            # Update ship_date and tracking if provided
            if ship_date and not existing.ship_date:
                existing.ship_date = ship_date
            if tracking_number and not existing.tracking_number:
                existing.tracking_number = tracking_number
            existing.updated_at = datetime.utcnow()
            return existing
    
    # Create new sales order
    order = SalesOrder(
        order_number=order_number,
        order_date=order_date,
        ship_date=ship_date,
        customer_id=customer_id,
        source=source,
        ss_order_id=ss_order_id,
        external_key=external_key,
        tracking_number=tracking_number,
        status="shipped" if ship_date else "pending",
        created_by_user_id=user.id if user else None,
        updated_by_user_id=user.id if user else None,
    )
    s.add(order)
    s.flush()
    return order


def _create_sales_order_line(
    s,
    *,
    sales_order_id: int,
    sku: str,
    quantity: int,
    lot_number: str | None = None,
    line_number: int | None = None,
) -> SalesOrderLine:
    """Create a sales order line item."""
    line = SalesOrderLine(
        sales_order_id=sales_order_id,
        sku=sku,
        quantity=quantity,
        lot_number=lot_number,
        line_number=line_number,
    )
    s.add(line)
    s.flush()
    return line


def run_sync(
    s, 
    *, 
    user: User, 
    start_date: date | None = None, 
    end_date: date | None = None
) -> ShipStationSyncRun:
    """
    Lean ShipStation sync:
    - Admin-triggered (sync request thread)
    - Idempotent per shipment+sku+lot (distribution_log_entries.external_key)
    - No background jobs
    - Supports optional date range for month-scoped sync
    
    Args:
        s: Database session
        user: User triggering the sync
        start_date: Optional start date (if None, uses SHIPSTATION_SINCE_DATE or 2025-01-01)
        end_date: Optional end date (if None, syncs to current date)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    api_key = (os.environ.get("SHIPSTATION_API_KEY") or "").strip()
    api_secret = (os.environ.get("SHIPSTATION_API_SECRET") or "").strip()
    if not api_key or not api_secret:
        raise ValueError("SHIPSTATION_API_KEY and SHIPSTATION_API_SECRET are required.")

    lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()

    # Hard limits to prevent runaway syncs
    # Increase defaults for better backfill coverage (2025+ orders)
    max_pages = int((os.environ.get("SHIPSTATION_MAX_PAGES") or "50").strip() or "50")
    max_orders = int((os.environ.get("SHIPSTATION_MAX_ORDERS") or "500").strip() or "500")

    # Determine start date: runtime param > env var > default
    if start_date:
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    else:
        since_date_str = (os.environ.get("SHIPSTATION_SINCE_DATE") or "").strip()
        if since_date_str:
            try:
                from datetime import date as date_type
                parsed_date = date_type.fromisoformat(since_date_str)
                start_dt = datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=timezone.utc)
            except Exception:
                start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        else:
            start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)

    client = ShipStationClient(api_key=api_key, api_secret=api_secret)
    lot_to_sku, lot_corrections = load_lot_log(lotlog_path)

    start = time.time()
    now = _now_utc()
    
    # Determine end date: runtime param > current time
    if end_date:
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        end_dt = now

    record_event(
        s,
        actor=user,
        action="shipstation.sync_started",
        entity_type="ShipStationSync",
        entity_id=None,
        metadata={
            "since_date": start_dt.date().isoformat(), 
            "end_date": end_dt.date().isoformat(),
            "max_pages": max_pages, 
            "max_orders": max_orders,
        },
    )

    orders_seen = 0
    shipments_seen = 0
    synced = 0
    skipped = 0
    hit_limit = False

    try:
        # Pre-fetch ALL shipments in date range (much faster than per-order fetching)
        # This reduces API calls from O(orders) to O(shipment_pages)
        logger.info("SYNC: Pre-fetching shipments from %s to %s...", start_dt.date().isoformat(), end_dt.date().isoformat())
        all_shipments: list[dict[str, Any]] = []
        for ship_page in range(1, max_pages + 1):
            chunk = client.list_shipments_by_date(
                ship_date_start=start_dt.date().isoformat(),
                ship_date_end=end_dt.date().isoformat(),
                page=ship_page,
                page_size=100,
            )
            if not chunk:
                break
            all_shipments.extend([x for x in chunk if isinstance(x, dict)])
            if len(chunk) < 100:
                break
        
        # Build order_id -> shipments lookup
        shipments_by_order: dict[str, list[dict[str, Any]]] = {}
        for sh in all_shipments:
            oid = str(sh.get("orderId") or "")
            if oid:
                shipments_by_order.setdefault(oid, []).append(sh)
        
        shipments_seen = len(all_shipments)
        logger.info("SYNC: Pre-fetched %d shipments across %d orders", shipments_seen, len(shipments_by_order))

        # Orders list (pagination) with hard limits
        for page in range(1, max_pages + 1):
            orders = client.list_orders(create_date_start=_iso_utc(start_dt), create_date_end=_iso_utc(now), page=page, page_size=100)
            if not orders:
                break

            for o in orders:
                # Check max_orders limit
                if orders_seen >= max_orders:
                    hit_limit = True
                    break

                orders_seen += 1
                order_id = str(o.get("orderId") or "")
                order_number = _safe_text(o.get("orderNumber"))
                if not order_id or not order_number:
                    skipped += 1
                    try:
                        with s.begin_nested():
                            s.add(
                                ShipStationSkippedOrder(
                                    order_id=order_id or None,
                                    order_number=order_number or None,
                                    reason="missing_order_id_or_number",
                                    details_json=json.dumps({"order": o}, default=str)[:4000],
                                )
                            )
                    except Exception:
                        pass
                    continue

                # Order data from list response (includes shipTo, items, internalNotes)
                # NO LONGER calling get_order() per order - massive performance improvement
                ship_to = o.get("shipTo") if isinstance(o.get("shipTo"), dict) else {}
                internal_notes = _safe_text(o.get("internalNotes"))
                items = o.get("items") if isinstance(o.get("items"), list) else []

                # Use pre-fetched shipments lookup (no per-order API calls!)
                shipments = shipments_by_order.get(order_id, [])

                if not shipments:
                    skipped += 1
                    try:
                        with s.begin_nested():
                            s.add(
                                ShipStationSkippedOrder(
                                    order_id=order_id,
                                    order_number=order_number,
                                    reason="no_shipments",
                                    details_json=json.dumps({"order_id": order_id, "order_number": order_number}, default=str),
                                )
                            )
                    except Exception:
                        pass
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
                    logger.warning("SYNC: order=%s no_valid_items, raw_items=%d", order_number, len(items))
                    try:
                        with s.begin_nested():
                            s.add(
                                ShipStationSkippedOrder(
                                    order_id=order_id,
                                    order_number=order_number,
                                    reason="no_valid_items",
                                    details_json=json.dumps({"items": items}, default=str)[:4000],
                                )
                            )
                    except Exception:
                        pass
                    continue

                logger.info("SYNC: order=%s sku_units=%s", order_number, sku_units)
                
                # === CANONICAL PIPELINE: Sales Order → Customer ===
                # 1. Try to find existing Sales Order by order_number (may have been imported via PDF)
                # 2. If found, use SO's customer (canonical source)
                # 3. If not found, try to find existing customer by ship_to
                # 4. If no customer found, distribution will have customer_id=None (admin matches later)
                
                existing_sales_order = (
                    s.query(SalesOrder)
                    .filter(SalesOrder.order_number == order_number)
                    .first()
                )
                
                if existing_sales_order and existing_sales_order.customer_id:
                    # Canonical path: Customer comes from existing Sales Order
                    customer = s.query(Customer).filter(Customer.id == existing_sales_order.customer_id).first()
                    logger.info("SYNC: order=%s matched existing SO id=%s, customer_id=%s", 
                               order_number, existing_sales_order.id, existing_sales_order.customer_id)
                else:
                    # Fallback: Try to find existing customer (DO NOT create new ones)
                    customer = _get_existing_customer_from_ship_to(s, ship_to)
                    if customer:
                        logger.info("SYNC: order=%s found existing customer id=%s", order_number, customer.id)
                    else:
                        logger.info("SYNC: order=%s no customer match - distribution will be unmatched", order_number)
                
                # Extract facility name from ship_to for distribution record (even without customer)
                facility_name = (
                    customer.facility_name if customer 
                    else _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name")) or "UNKNOWN"
                )

                # Extract per-SKU lots from internal notes (e.g., "SKU: 21600101003 LOT: SLQ-05012025")
                sku_lot_pairs = extract_sku_lot_pairs(internal_notes)
                
                # Fallback: single lot extraction for orders without per-SKU notation
                raw_lot = extract_lot(internal_notes)
                fallback_lot = normalize_lot(raw_lot) if raw_lot else "UNKNOWN"
                
                # Apply LotLog corrections if available (e.g., SLQ-050220 -> SLQ-05022025)
                if fallback_lot in lot_corrections:
                    fallback_lot = lot_corrections[fallback_lot]

                # === SALES ORDER HANDLING ===
                # Parse order_date from ShipStation createDate (falls back to now)
                order_create_date_str = _safe_text(o.get("createDate") or o.get("orderDate"))
                try:
                    order_date = date_type.fromisoformat(order_create_date_str[:10]) if order_create_date_str else now.date()
                except Exception:
                    order_date = now.date()
                
                # Parse ship_date from first shipment
                first_ship_date_str = _safe_text(shipments[0].get("shipDate")) if shipments else None
                try:
                    first_ship_date = date_type.fromisoformat(first_ship_date_str[:10]) if first_ship_date_str else None
                except Exception:
                    first_ship_date = None
                
                # First tracking number
                first_tracking = _safe_text(shipments[0].get("trackingNumber")) if shipments else None
                
                # Use existing Sales Order if found (from PDF import)
                sales_order = existing_sales_order
                sales_order_external_key = f"ss:{order_id}"
                
                # Only create new Sales Order if:
                # 1. No existing SO found, AND
                # 2. We have a customer (canonical source)
                # Otherwise, distribution will be unmatched (admin matches via PDF import later)
                if not sales_order and customer:
                    try:
                        with s.begin_nested():
                            sales_order = _find_or_create_sales_order(
                                s,
                                order_number=order_number,
                                order_date=order_date,
                                ship_date=first_ship_date,
                                customer_id=customer.id,
                                source="shipstation",
                                ss_order_id=order_id,
                                external_key=sales_order_external_key,
                                tracking_number=first_tracking,
                                user=user,
                            )
                            
                            # Create sales order lines for each SKU (if not already created)
                            existing_lines = {(l.sku, l.quantity): l for l in (sales_order.lines or [])}
                            line_num = 1
                            for sku, units in sku_units.items():
                                lot_for_line = sku_lot_pairs.get(sku) or fallback_lot
                                if lot_for_line in lot_corrections:
                                    lot_for_line = lot_corrections[lot_for_line]
                                
                                if (sku, units) not in existing_lines:
                                    _create_sales_order_line(
                                        s,
                                        sales_order_id=sales_order.id,
                                        sku=sku,
                                        quantity=units,
                                        lot_number=lot_for_line,
                                        line_number=line_num,
                                    )
                                line_num += 1
                    except IntegrityError:
                        # Sales order already exists (race condition or duplicate) - fetch it
                        sales_order = (
                            s.query(SalesOrder)
                            .filter(SalesOrder.source == "shipstation", SalesOrder.external_key == sales_order_external_key)
                            .first()
                        )
                
                # If still no sales order and no customer, log for admin review
                if not sales_order and not customer:
                    logger.info("SYNC: order=%s will create unmatched distribution (no SO, no customer)", order_number)
                
                logger.info("SYNC: order=%s sales_order_id=%s processing %d shipments", order_number, sales_order.id, len(shipments))

                for sh in shipments:
                    shipment_id = _safe_text(sh.get("shipmentId")) or _safe_text(sh.get("shipment_id"))
                    ship_date = _safe_text(sh.get("shipDate")) or _safe_text(sh.get("ship_date"))
                    tracking = _safe_text(sh.get("trackingNumber")) or _safe_text(sh.get("tracking_number"))

                    if not shipment_id:
                        logger.warning("SYNC: order=%s shipment missing shipmentId! keys=%s", order_number, list(sh.keys())[:10])
                        continue

                    for sku, units in sku_units.items():
                        # Use per-SKU lot if available, otherwise fallback
                        lot_for_row = sku_lot_pairs.get(sku) or fallback_lot
                        
                        # Apply corrections to per-SKU lot too
                        if lot_for_row in lot_corrections:
                            lot_for_row = lot_corrections[lot_for_row]

                        external_key = _build_external_key(shipment_id=shipment_id, sku=sku, lot_number=lot_for_row)

                        # Customer comes from Sales Order (canonical) if available
                        effective_customer_id = (
                            sales_order.customer_id if sales_order and sales_order.customer_id
                            else (customer.id if customer else None)
                        )
                        
                        payload = {
                            "ship_date": ship_date[:10] if ship_date else now.date().isoformat(),
                            "order_number": order_number,
                            "facility_name": facility_name,
                            "customer_id": str(effective_customer_id) if effective_customer_id else "",
                            "customer_name": facility_name,  # Use extracted facility_name
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
                            # Link to sales order (source of truth)
                            "sales_order_id": str(sales_order.id) if sales_order else None,
                        }

                        logger.info("SYNC: attempting insert order=%s sku=%s lot=%s ext_key=%s sales_order_id=%s", order_number, sku, lot_for_row, external_key[:50], sales_order.id if sales_order else None)
                        try:
                            # Use a SAVEPOINT so idempotent duplicates don't roll back the whole sync.
                            with s.begin_nested():
                                e = create_distribution_entry(s, payload, user=user, source_default="shipstation")
                                e.external_key = external_key
                                # Link to sales order
                                if sales_order:
                                    e.sales_order_id = sales_order.id
                                s.flush()  # force unique index check now
                            synced += 1
                            logger.info("SYNC: SUCCESS order=%s sku=%s sales_order_id=%s", order_number, sku, sales_order.id if sales_order else None)
                        except IntegrityError as ie:
                            skipped += 1
                            logger.warning("SYNC: duplicate order=%s ext_key=%s err=%s", order_number, external_key[:50], str(ie)[:100])
                            # Try to log skip record, but don't fail if it already exists
                            try:
                                with s.begin_nested():
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
                            except Exception:
                                pass  # Skip record already exists, ignore
                        except Exception as exc:
                            skipped += 1
                            logger.error("SYNC: FAILED order=%s sku=%s err=%s", order_number, sku, str(exc))
                            try:
                                with s.begin_nested():
                                    s.add(
                                        ShipStationSkippedOrder(
                                            order_id=order_id,
                                            order_number=order_number,
                                            reason="insert_failed",
                                            details_json=json.dumps({
                                                "error": str(exc),
                                                "error_type": type(exc).__name__,
                                                "external_key": external_key,
                                                "sku": sku,
                                                "lot": lot_for_row,
                                                "facility": facility_name[:100],
                                            }, default=str)[:4000],
                                        )
                                    )
                            except Exception:
                                pass  # Skip record already exists, ignore

            # Break outer loop if hit order limit
            if hit_limit:
                break

        duration = int(time.time() - start)
        if hit_limit:
            limit_msg = f" ⚠️ LIMIT REACHED: Only processed {orders_seen} orders (max={max_orders}). Increase SHIPSTATION_MAX_ORDERS for full backfill."
        else:
            limit_msg = " All available orders processed."
        run = ShipStationSyncRun(
            synced_count=synced,
            skipped_count=skipped,
            orders_seen=orders_seen,
            shipments_seen=shipments_seen,
            duration_seconds=duration,
            message=f"Synced={synced} skipped={skipped}.{limit_msg}",
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

