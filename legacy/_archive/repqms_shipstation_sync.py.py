import json
import re
import csv
from datetime import datetime, timezone, timedelta
import requests
from requests.auth import HTTPBasicAuth
from typing import Any

# Import canonical field normalization (to avoid circular import, we'll define a stub here
# and the real implementation will be injected from Proto1.py when sync is called)
_normalize_fields_json_fn = None
_customer_resolver_fn = None
_rep_assigner_fn = None
_rep_picker_fn = None


def _ssync_log(level: str, message: str, **ctx: Any) -> None:
    """Structured-ish logging for ShipStation sync. Never raises."""
    try:
        payload = {"level": level, "msg": message, **{k: v for k, v in ctx.items() if v is not None}}
        print(f"[SHIPSTATION_SYNC] {json.dumps(payload, default=str)[:2000]}", flush=True)
    except Exception:
        try:
            print(f"[SHIPSTATION_SYNC] {level} {message}", flush=True)
        except Exception:
            pass


def _as_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> list:
    return v if isinstance(v, list) else []


def _safe_text(v: Any) -> str:
    try:
        return (v or "").strip()
    except Exception:
        return ""


def _infer_item_sku(it: dict) -> str | None:
    """Best-effort SKU inference from sku/name fields; never raises."""
    try:
        raw_sku = _safe_text(it.get("sku")).upper()
        name = _safe_text(it.get("name")).upper()
        return canonicalize_sku(raw_sku) or canonicalize_sku(name)
    except Exception:
        return None


def ensure_skipped_table(execute_db):
    """Create skipped orders table once for diagnostics."""
    execute_db(
        """
        CREATE TABLE IF NOT EXISTS shipstation_skipped_orders (
            id SERIAL PRIMARY KEY,
            order_id TEXT,
            order_number TEXT,
            order_date TEXT,
            reason TEXT,
            details JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    execute_db("CREATE UNIQUE INDEX IF NOT EXISTS idx_skipped_order_id ON shipstation_skipped_orders(order_id)")


def record_skipped_order(execute_db, order_id: str, order_number: str, order_date: str, reason: str, details: dict):
    """Persist skipped order diagnostics for admin review."""
    try:
        execute_db(
            """
            INSERT INTO shipstation_skipped_orders (order_id, order_number, order_date, reason, details, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (order_id) DO UPDATE
            SET reason = EXCLUDED.reason,
                details = EXCLUDED.details,
                updated_at = CURRENT_TIMESTAMP,
                order_number = EXCLUDED.order_number,
                order_date = EXCLUDED.order_date
            """,
            (order_id, order_number, order_date, reason, json.dumps(details or {}))
        )
    except Exception:
        # Diagnostics should never break sync; swallow errors
        pass


def record_sync_run(execute_db, message: str, synced: int, skipped: int, orders_seen: int, shipments_seen: int, duration_seconds: int):
    """Persist high-level sync summary for dashboard display."""
    try:
        execute_db(
            """
            CREATE TABLE IF NOT EXISTS shipstation_sync_runs (
                id SERIAL PRIMARY KEY,
                ran_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message TEXT,
                synced INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                orders_seen INTEGER DEFAULT 0,
                shipments_seen INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0
            )
            """
        )
        execute_db("ALTER TABLE shipstation_sync_runs ADD COLUMN IF NOT EXISTS orders_seen INTEGER DEFAULT 0")
        execute_db("ALTER TABLE shipstation_sync_runs ADD COLUMN IF NOT EXISTS shipments_seen INTEGER DEFAULT 0")
        execute_db("ALTER TABLE shipstation_sync_runs ADD COLUMN IF NOT EXISTS duration_seconds INTEGER DEFAULT 0")
        execute_db(
            """
            INSERT INTO shipstation_sync_runs (ran_at, message, synced, skipped, orders_seen, shipments_seen, duration_seconds)
            VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s)
            """,
            (message, synced, skipped, orders_seen, shipments_seen, duration_seconds),
        )
    except Exception:
        pass

def set_normalize_fields_json_fn(fn):
    """Set the normalize_fields_json function from Proto1.py to avoid circular imports"""
    global _normalize_fields_json_fn
    _normalize_fields_json_fn = fn


def set_customer_helper_fns(resolve_customer_fn, assign_rep_fn, pick_rep_fn):
    """Inject customer/responsible rep helper callbacks from Proto1.py"""
    global _customer_resolver_fn, _rep_assigner_fn, _rep_picker_fn
    _customer_resolver_fn = resolve_customer_fn
    _rep_assigner_fn = assign_rep_fn
    _rep_picker_fn = pick_rep_fn


def normalize_company_key(name: str) -> str:
    """SS4-style company key normalization: alphanumeric only, max 15 chars"""
    if not name:
        return ""
    # Expand common abbreviations (minimize cryptic abbreviations)
    name = (name or "").strip()
    # Replace & with AND
    name = re.sub(r"\s*&\s*", " AND ", name, flags=re.IGNORECASE)
    # Expand common medical abbreviations
    abbrev_map = {
        r"\bURO\b": "UROLOGY",
        r"\bCTR\b": "CENTER",
        r"\bCTR\.\b": "CENTER",
        r"\bCTR,\b": "CENTER",
        r"\bCTR$": "CENTER",
        r"\bCTR\.?$": "CENTER",
        r"\bMED\b": "MEDICAL",
        r"\bHOSP\b": "HOSPITAL",
        r"\bASSOC\b": "ASSOCIATES",
    }
    for rx, repl in abbrev_map.items():
        name = re.sub(rx, repl, name, flags=re.IGNORECASE)
    base = re.sub(r"[^A-Z0-9 ]", "", re.sub(r"\s+", " ", name.strip().upper()))
    return base[:15]


def canonicalize_sku(raw: str) -> str | None:
    """Convert SKU variants to canonical form"""
    s = (raw or "").upper()
    if "14" in s:
        return "211410SPT"
    if "16" in s:
        return "211610SPT"
    if "18" in s:
        return "211810SPT"
    # Accept explicit SKUs as-is if they match known pattern
    if re.match(r"^\d{6}SPT$", s):
        return s
    return None


def normalize_lot(code: str) -> str:
    """Normalize lot code to SLQ-XXXXXXXX format"""
    c = (code or "").strip().upper()
    if c and not c.startswith("SLQ-") and c.startswith("SLQ"):
        c = "SLQ-" + c[3:]
    return c if c.startswith("SLQ-") else f"SLQ-{c}"


def load_lot_log(filepath: str = "LotLog.csv") -> dict:
    """Load lot → SKU mapping from LotLog.csv"""
    lot_to_sku = {}
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lot = row.get('Lot', '').strip()
                sku = row.get('SKU', '').strip()
                if lot and sku:
                    # Normalize the lot and store multiple variations
                    lot_upper = lot.upper()
                    normalized_lot = normalize_lot(lot_upper)
                    lot_to_sku[lot_upper] = sku
                    lot_to_sku[normalized_lot] = sku
                    # Also store without SLQ- prefix for matching
                    if normalized_lot.startswith("SLQ-"):
                        lot_to_sku[normalized_lot[4:]] = sku
            print(f"Loaded {len(lot_to_sku)} lot mappings")
    except Exception as e:
        print(f"Could not load LotLog: {e}")
    return lot_to_sku


# Regex patterns for lot extraction (from SS4)
lot_rx = re.compile(r"LOT[:\s]*([A-Z0-9\-]+)", re.IGNORECASE)
bare_lot_rx = re.compile(r"\bSLQ-?[A-Z0-9\-]{5,}\b", re.IGNORECASE)
cf_rx = re.compile(r"SKU[:\s]*([A-Z0-9]+SPT)\s*LOT[:\s]*([A-Z0-9\-]+)", re.IGNORECASE)


def parse_sku_lot(text: str) -> list:
    """Parse SKU:LOT pairs from custom field text"""
    return [(sku.upper(), normalize_lot(lot.upper())) for sku, lot in cf_rx.findall(text or "")]


def _update_baseline(baseline: dict, sku: str, weight_per_unit: float):
    """Track running averages for pack/unit weights to disambiguate 10-pack vs single."""
    total, count = baseline.get(sku, (0.0, 0))
    baseline[sku] = (total + weight_per_unit, count + 1)


def _mean_baseline(baseline: dict, sku: str) -> float | None:
    total, count = baseline.get(sku, (0.0, 0))
    if count == 0:
        return None
    return total / count


def classify_quantity(it: dict, pack_baseline: dict, unit_baseline: dict) -> tuple[int, int]:
    """Return (packs, units) for an item using SS4 heuristics."""
    name = (it.get("name") or "").lower()
    qty = int(it.get("quantity", 0) or 0)
    weight_val = (it.get("weight") or {}).get("value")
    canon = canonicalize_sku(it.get("sku", ""))

    if qty <= 0:
        return 0, 0

    # Explicit name hints win
    if "10-pack" in name or "10 pack" in name or "10pk" in name:
        return qty, qty * 10
    if "single" in name:
        return 0, qty

    # Use weight baselines if present
    if canon and weight_val and qty:
        ratio = weight_val / qty
        pb = _mean_baseline(pack_baseline, canon)
        ub = _mean_baseline(unit_baseline, canon)
        if pb and ub:
            return (0, qty) if abs(ratio - ub) < abs(ratio - pb) else (qty, qty * 10)
        if pb:
            return (qty, qty * 10) if ratio > pb * 0.75 else (0, qty)
        if ub:
            return (0, qty) if ratio < ub * 1.25 else (qty, qty * 10)

    # Default: treat as singles
    return 0, qty


def sync_units_and_grouping(
    api_key: str,
    api_secret: str,
    default_rep_id: int,
    query_db,
    execute_db,
    days: int = 30,
    start_date_override: str | None = None,
    max_orders: int = 500,
    force_rescan: bool = False,
    progress_callback=None,
    throttle_seconds: int = 60,
    should_cancel_fn=None,
) -> tuple[bool, str]:
    """
    Enhanced ShipStation sync following SS4.py logic:
    - Fetches order details with items
    - Parses internal notes for lot numbers
    - Uses LotLog to map lots → SKUs
    - Extracts SKU/Lot/Qty for each item
    - Creates separate device_distribution_records per SKU/Lot pair
    
    Args:
        progress_callback: Optional function(synced, skipped, current_page, status, message) 
                          to report progress during sync
    """
    import time
    start_time = time.time()

    if not api_key or not api_secret:
        return False, "ShipStation API credentials not configured"

    # Ensure diagnostics table exists
    ensure_skipped_table(execute_db)

    # Load lot mappings
    lot_to_sku = load_lot_log()

    session = requests.Session()
    session.auth = HTTPBasicAuth(api_key, api_secret)
    request_timeout = 120  # allow large date windows to respond

    end_date = datetime.now(timezone.utc)
    if start_date_override:
        try:
            start_date = datetime.fromisoformat(start_date_override + "T00:00:00+00:00")
        except Exception:
            start_date = end_date - timedelta(days=days)
    else:
        start_date = end_date - timedelta(days=days)

    orders_url = "https://ssapi.shipstation.com/orders"
    params = {
        # createDate filters respond faster than orderDate for large windows
        "createDateStart": start_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-1] + "0",
        "createDateEnd": end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-1] + "0",
        "page": 1,
        "pageSize": 100,
    }

    synced = 0
    skipped = 0
    orders_seen = 0
    shipments_seen = 0

    # Track pack vs unit weights to classify ambiguous SKUs the way SS4 does
    pack_baseline: dict[str, tuple[float, int]] = {}
    unit_baseline: dict[str, tuple[float, int]] = {}

    _ssync_log("info", "sync_started", days=days, start_date_override=start_date_override, 
              max_orders=max_orders, throttle_seconds=throttle_seconds)

    if progress_callback:
        progress_callback(synced=0, skipped=0, current_page=0, status='running', 
                         message='Starting ShipStation sync...')

    for page in range(1, 200):  # Increased page limit for full deep scan
        # Cancellation check before each page
        if callable(should_cancel_fn) and should_cancel_fn():
            msg = f"Sync canceled by user after {synced} synced, {skipped} skipped"
            if progress_callback:
                progress_callback(synced=synced, skipped=skipped, current_page=page,
                                  status='completed', message=msg)
            return True, msg
        # Report progress
        if progress_callback:
            elapsed = int(time.time() - start_time)
            progress_callback(synced=synced, skipped=skipped, current_page=page, 
                            status='running', 
                            message=f'Checking page {page}... (Synced: {synced}, Skipped: {skipped}, Elapsed: {elapsed}s)')

        # Count check
        if synced >= max_orders:
            msg = f"Synced {synced} orders (reached max limit of {max_orders})"
            if progress_callback:
                progress_callback(synced=synced, skipped=skipped, current_page=page, 
                                status='completed', message=msg)
            return True, msg

        params["page"] = page
        # Robust fetch with retries/backoff
        orders = []
        retries = 0
        last_err = None
        while retries < 5:
            try:
                r = session.get(orders_url, params=params, timeout=request_timeout)
                if r.status_code == 429:
                    # Rate limited; backoff
                    wait = min(throttle_seconds, 60) or 60
                    if progress_callback:
                        progress_callback(synced=synced, skipped=skipped, current_page=page,
                                          status='running', message=f'Rate limited. Waiting {wait}s...')
                    time.sleep(wait)
                    retries += 1
                    continue
                r.raise_for_status()
                orders = r.json().get("orders", []) or []
                break
            except Exception as e:
                last_err = e
                # Backoff progressively
                wait = min(throttle_seconds * (retries + 1), 120)
                if progress_callback:
                    progress_callback(synced=synced, skipped=skipped, current_page=page,
                                      status='running', message=f'API error, retry {retries+1}/5 in {wait}s')
                time.sleep(wait)
                retries += 1
        if not orders and last_err:
            # Move on to next page and continue; preserve progress
            if progress_callback:
                progress_callback(synced=synced, skipped=skipped, current_page=page, status='running',
                                  message=f'Page {page} failed after retries: {str(last_err)[:80]}')
            # Optional throttle between pages even when failing
            if throttle_seconds:
                time.sleep(throttle_seconds)
            continue

        if not orders:
            break

        orders_fetched = len(orders)
        _ssync_log("info", "fetched_orders_page", page=page, count=orders_fetched, 
                  synced=synced, skipped=skipped, elapsed_seconds=int(time.time() - start_time))
        
        # Heartbeat: Update progress immediately after fetching orders
        if progress_callback:
            elapsed = int(time.time() - start_time)
            progress_callback(synced=synced, skipped=skipped, current_page=page,
                            status='running',
                            message=f'Fetched {orders_fetched} orders from page {page} (Synced: {synced}, Skipped: {skipped}, Orders seen: {orders_seen}, Elapsed: {elapsed}s)')

        for o in orders:
            # Count check
            if synced >= max_orders:
                break

            orders_seen += 1
            
            # Heartbeat: Update progress every 5 orders processed (shows activity even if no synced yet)
            if progress_callback and orders_seen % 5 == 0:
                elapsed = int(time.time() - start_time)
                progress_callback(synced=synced, skipped=skipped, current_page=page,
                                status='running',
                                message=f'Processing order {orders_seen}... (Synced: {synced}, Skipped: {skipped}, Elapsed: {elapsed}s)')

            # Do not rely solely on orderStatus; we will use shipments presence later
            order_number = o.get("orderNumber", "")
            if not order_number:
                continue

            # Clear any legacy aggregated rows for this order (without ss_shipment_id)
            legacy_rows = query_db(
                "SELECT id FROM devices_distributed WHERE order_number = %s AND source='shipstation' AND ss_shipment_id IS NULL",
                (order_number,),
            ) or []
            for row in legacy_rows:
                execute_db("DELETE FROM device_distribution_records WHERE dist_id=%s", (row["id"],))
                execute_db("DELETE FROM new_customer_records WHERE dist_id=%s", (row["id"],))
                execute_db("DELETE FROM devices_distributed WHERE id=%s", (row["id"],))

            oid = o.get("orderId")

            try:
                # Fetch order details
                # Details with retry/backoff
                det = {}
                det_retries = 0
                while det_retries < 5:
                    try:
                        dr = session.get(f"https://ssapi.shipstation.com/orders/{oid}", timeout=30)
                        if dr.status_code == 429:
                            time.sleep(min(throttle_seconds, 60) or 60)
                            det_retries += 1
                            continue
                        dr.raise_for_status()
                        det_raw = dr.json()
                        det = _as_dict(det_raw)
                        if not det:
                            raise ValueError(f"order details not a dict (type={type(det_raw).__name__})")
                        break
                    except Exception:
                        time.sleep(min(throttle_seconds * (det_retries + 1), 120))
                        det_retries += 1
                ship_to = _as_dict(det.get("shipTo"))
                facility = _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name"))
                addr1 = _safe_text(ship_to.get("street1") or ship_to.get("address1"))
                addr2 = _safe_text(ship_to.get("street2") or ship_to.get("address2"))
                city = _safe_text(ship_to.get("city"))
                state = _safe_text(ship_to.get("state") or ship_to.get("stateCode"))
                postal = _safe_text(ship_to.get("postalCode") or ship_to.get("postal"))
                company_key = normalize_company_key(facility)

                # Get internal notes for lot extraction
                notes = _safe_text(det.get("internalNotes")).upper()

                items = _as_list(det.get("items"))
                
                # Build SKU map from items with pack/unit classification
                sku_map = {}
                for it_raw in items:
                    it = _as_dict(it_raw)
                    raw_sku = _safe_text(it.get("sku")).upper()
                    canon = _infer_item_sku(it)
                    if raw_sku == "SLQ-4007" or canon == "SLQ-4007":  # Ignore this SKU
                        continue
                    if not canon:
                        continue

                    # Update baselines when names explicitly indicate pack or single
                    qty = int(it.get("quantity", 0) or 0)
                    weight_val = (it.get("weight") or {}).get("value")
                    name_l = (it.get("name") or "").lower()
                    if qty > 0 and weight_val:
                        if "10-pack" in name_l or "10 pack" in name_l or "10pk" in name_l:
                            _update_baseline(pack_baseline, canon, weight_val / qty)
                        elif "single" in name_l:
                            _update_baseline(unit_baseline, canon, weight_val / qty)

                    packs, units = classify_quantity(it, pack_baseline, unit_baseline)
                    total_units = units if units else packs * 10
                    sku_map[canon] = sku_map.get(canon, 0) + total_units

                # Collect (sku, lot, qty) tuples
                pairs = []
                seen_pairs = set()

                # A) Internal notes: "LOT: <code>"
                for lot in lot_rx.findall(notes):
                    lotn = normalize_lot(lot)
                    # Try multiple variations for lot lookup
                    sku = (lot_to_sku.get(lotn) or 
                           lot_to_sku.get(lot.upper()) or
                           lot_to_sku.get(lotn[4:] if lotn.startswith("SLQ-") else lotn))
                    if sku in sku_map:
                        qty = sku_map[sku]
                        if (sku, lotn) not in seen_pairs:
                            pairs.append((sku, lotn, qty))
                            seen_pairs.add((sku, lotn))

                # B) Bare lots: "SLQ-#########"
                for raw_lot in bare_lot_rx.findall(notes):
                    lotn = normalize_lot(raw_lot)
                    # Try multiple variations for lot lookup
                    sku = (lot_to_sku.get(lotn) or 
                           lot_to_sku.get(raw_lot.upper()) or
                           lot_to_sku.get(lotn[4:] if lotn.startswith("SLQ-") else lotn))
                    if sku in sku_map:
                        qty = sku_map[sku]
                        if (sku, lotn) not in seen_pairs:
                            pairs.append((sku, lotn, qty))
                            seen_pairs.add((sku, lotn))

                # C) Fallback: customField2 → customField1
                # Data contract: advancedOptions must be a dict (can be empty)
                if not pairs:
                    advanced_options = det.get("advancedOptions", {}) or {}
                    if not isinstance(advanced_options, dict):
                        advanced_options = {}
                    
                    for cf in ("customField2", "customField1"):
                        txt = advanced_options.get(cf, "") or ""
                        try:
                            parsed_pairs = parse_sku_lot(txt)
                            if parsed_pairs:
                                for pair in parsed_pairs:
                                    try:
                                        if len(pair) >= 2:
                                            sku, lotn = pair[0], pair[1]
                                            if sku in sku_map:
                                                qty = sku_map[sku]
                                                if (sku, lotn) not in seen_pairs:
                                                    pairs.append((sku, lotn, qty))
                                                    seen_pairs.add((sku, lotn))
                                    except (IndexError, ValueError, TypeError) as e:
                                        print(f"[SHIPSTATION SYNC] Skipping malformed SKU/LOT pair in {cf}: {e}")
                                        continue  # Skip this pair, continue with next
                        except Exception as e:
                            print(f"[SHIPSTATION SYNC] Error parsing {cf}: {e}. Skipping field.")
                            continue  # Skip this field, continue with next
                        if pairs:
                            break

                # D) If still no pairs, create entries with "UNKNOWN" lot
                if not pairs and sku_map:
                    for sku, qty in sku_map.items():
                        pairs.append((sku, "UNKNOWN", qty))

                # Get ship date across all shipments (pagination to match SS4)
                shipments = []
                sh_retries = 0
                page_s = 1
                while sh_retries < 5:
                    try:
                        sr = session.get(
                            "https://ssapi.shipstation.com/shipments",
                            params={"orderId": oid, "page": page_s, "pageSize": 100},
                            timeout=request_timeout,
                        )
                        if sr.status_code == 429:
                            time.sleep(min(throttle_seconds, 60) or 60)
                            sh_retries += 1
                            continue
                        sr.raise_for_status()
                        srj = _as_dict(sr.json())
                        chunk = _as_list(srj.get("shipments"))
                        shipments.extend(chunk)
                        if len(chunk) < 100:
                            break
                        page_s += 1
                    except Exception:
                        time.sleep(min(throttle_seconds * (sh_retries + 1), 120))
                        sh_retries += 1
                shipments_seen += len(shipments)
                
                # Heartbeat: Update progress when shipments are fetched (shows activity)
                if progress_callback and len(shipments) > 0:
                    elapsed = int(time.time() - start_time)
                    progress_callback(synced=synced, skipped=skipped, current_page=page,
                                    status='running',
                                    message=f'Found {len(shipments)} shipment(s) for order {order_number} (Orders: {orders_seen}, Shipments: {shipments_seen}, Elapsed: {elapsed}s)')
                
                # If there are no shipments and order isn't marked shipped, skip this order
                if not shipments and (o.get("orderStatus", "") or "").lower() != "shipped":
                    # Consider it not yet shipped; don't create records
                    record_skipped_order(
                        execute_db,
                        str(o.get("orderId")),
                        order_number,
                        o.get("orderDate"),
                        "awaiting_shipment",
                        {"status": o.get("orderStatus"), "note": "No shipments returned"},
                    )
                    skipped += 1
                    # Progress update occasionally
                    if progress_callback and skipped % 25 == 0:
                        elapsed = int(time.time() - start_time)
                        progress_callback(synced=synced, skipped=skipped, current_page=page,
                                          status='running',
                                          message=f'Awaiting shipment orders skipped: {skipped} (Elapsed: {elapsed}s)')
                    continue
                # Safely extract ship dates with guards
                ship_dates = []
                for s in shipments:
                    try:
                        ship_date_val = s.get("shipDate") if isinstance(s, dict) else None
                        if ship_date_val:
                            ship_dates.append(ship_date_val)
                    except (AttributeError, TypeError):
                        continue
                ship_date = max(ship_dates) if ship_dates else o.get("orderDate")

            except Exception as e:
                # Skip this order if API calls fail
                record_skipped_order(
                    execute_db,
                    str(o.get("orderId")),
                    order_number,
                    o.get("orderDate"),
                    "fetch_error",
                    {"error": str(e)},
                )
                continue

            # If a shipped order returns zero shipments, create a fallback shipment using order items
            if not shipments:
                shipments = [{"shipmentId": f"order-{oid}-fallback", "shipDate": o.get("orderDate"), "shipmentItems": det.get("items", [])}]
                shipments_seen += len(shipments)

            # Map sku -> lot (first seen) for quick lookup
            sku_lot_map = {}
            for pair in pairs:
                try:
                    # Guard against tuple unpacking errors
                    if isinstance(pair, (tuple, list)) and len(pair) >= 2:
                        sku = pair[0] if len(pair) > 0 else None
                        lot = pair[1] if len(pair) > 1 else None
                        if sku and lot and sku not in sku_lot_map:
                            sku_lot_map[sku] = lot
                except (IndexError, ValueError, TypeError, AttributeError) as e:
                    _ssync_log("warn", "skipped_malformed_pair", pair=str(pair)[:100], error=str(e)[:100])
                    continue
            if not sku_lot_map and sku_map:
                for sku in sku_map:
                    sku_lot_map[sku] = "UNKNOWN"

            # Allow allocation of order-level items once if shipments lack item details
            order_sku_map_remaining = dict(sku_map)

            customer = None
            customer_id = None
            chosen_rep_id = default_rep_id
            if callable(_customer_resolver_fn):
                try:
                    customer = _customer_resolver_fn(
                        facility_name=facility,
                        city=city,
                        state=state,
                        address1=addr1,
                        address2=addr2,
                        zip_code=postal,
                    )
                    customer_id = customer.get("id") if isinstance(customer, dict) else None
                except Exception:
                    customer = None
                    customer_id = None
            if callable(_rep_picker_fn):
                try:
                    chosen_rep_id = _rep_picker_fn(customer_id, fallback_rep_id=default_rep_id)
                except Exception:
                    chosen_rep_id = default_rep_id
            if callable(_rep_assigner_fn) and customer_id and chosen_rep_id:
                try:
                    _rep_assigner_fn(customer_id, chosen_rep_id, make_primary_if_none=True)
                except Exception:
                    pass

            order_failed = False
            for idx, sh_raw in enumerate(shipments):
                try:
                    sh = _as_dict(sh_raw)
                    if not sh:
                        _ssync_log("warn", "skipped_empty_shipment", orderNumber=order_number, 
                                  shipment_index=idx)
                        continue
                except (AttributeError, TypeError) as e:
                    _ssync_log("warn", "skipped_invalid_shipment", orderNumber=order_number, 
                              shipment_index=idx, error=str(e)[:100])
                    continue
                
                # Safe extraction of shipment ID with fallback
                ss_ship_id = None
                for key in ["shipmentId", "shipment_id", "shipmentID", "id"]:
                    try:
                        val = sh.get(key)
                        if val:
                            ss_ship_id = str(val)
                            break
                    except (AttributeError, TypeError):
                        continue
                if not ss_ship_id:
                    ss_ship_id = f"{order_number}-{page}-{idx}"
                
                tracking = sh.get("trackingNumber") or sh.get("trackingNumberPublic") or ""
                ship_date = sh.get("shipDate") or o.get("orderDate")
                ship_items = _as_list(sh.get("shipmentItems"))

                shipment_sku_map = {}
                for it_raw in ship_items:
                    try:
                        it = _as_dict(it_raw)
                        if not it:
                            continue
                        canon = _infer_item_sku(it)
                        if not canon:
                            continue
                        packs, units = classify_quantity(it, pack_baseline, unit_baseline)
                        qty_units = units if units else packs * 10
                        if qty_units <= 0:
                            try:
                                qty_val = it.get("quantity", 0) or 0
                                qty_units = int(qty_val) if qty_val else 0
                            except (ValueError, TypeError):
                                qty_units = 0
                        if qty_units <= 0:
                            continue
                        shipment_sku_map[canon] = shipment_sku_map.get(canon, 0) + qty_units
                    except (AttributeError, TypeError, KeyError) as e:
                        _ssync_log("warn", "skipped_invalid_item", orderNumber=order_number, 
                                  shipmentId=ss_ship_id, error=str(e)[:100])
                        continue

                if not shipment_sku_map and order_sku_map_remaining:
                    shipment_sku_map = order_sku_map_remaining
                    order_sku_map_remaining = {}

                if not shipment_sku_map:
                    continue

                try:
                    existing_shipment = query_db(
                        "SELECT id FROM devices_distributed WHERE ss_shipment_id=%s",
                        (ss_ship_id,),
                        one=True,
                    )
                    if existing_shipment:
                        dist_id = existing_shipment["id"]
                        execute_db(
                            """UPDATE devices_distributed 
                               SET order_number=%s, 
                                   ship_date=%s, 
                                   tracking_number=%s,
                                   rep_id=COALESCE(rep_id, %s), 
                                   customer_id=COALESCE(customer_id, %s)
                               WHERE id=%s""",
                            (order_number, ship_date, tracking, chosen_rep_id, customer_id, dist_id),
                        )
                        execute_db(
                            """DELETE FROM device_distribution_records 
                               WHERE dist_id=%s 
                               AND (
                                   (stored_filename LIKE 'SS_%' OR original_filename = 'SHIPSTATION')
                                   AND
                                   NOT (
                                       fields_json::text ILIKE '%"Record Type": "shipment_record"%'
                                       OR fields_json::text ILIKE '%"record_type": "shipment_record"%'
                                       OR fields_json::text ILIKE '%"type": "shipment_record"%'
                                       OR fields_json::text ILIKE '%"Record Type": "distribution_record"%'
                                       OR fields_json::text ILIKE '%"record_type": "distribution_record"%'
                                       OR fields_json::text ILIKE '%"type": "distribution_record"%'
                                       OR fields_json::text ILIKE '%"Record Type": "document"%'
                                       OR fields_json::text ILIKE '%"Record Type": "attachment"%'
                                       OR fields_json::text ILIKE '%"Source": "shipment_record"%'
                                       OR fields_json::text ILIKE '%"source": "shipment_record"%'
                                       OR fields_json::text ILIKE '%"Source": "distribution_record"%'
                                       OR fields_json::text ILIKE '%"source": "distribution_record"%'
                                   )
                               )""",
                            (dist_id,),
                        )
                        execute_db(
                            """DELETE FROM new_customer_records 
                               WHERE dist_id=%s 
                               AND (stored_filename = 'SHIPSTATION' OR stored_filename LIKE 'SS_%')""",
                            (dist_id,),
                        )
                    else:
                        dist_id = execute_db(
                            "INSERT INTO devices_distributed (rep_id, order_number, ship_date, source, created_at, tracking_number, ss_shipment_id, customer_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                            (chosen_rep_id, order_number, ship_date, "shipstation", datetime.now(), tracking, ss_ship_id, customer_id),
                            returning_id=True,
                        )
                except Exception as e:
                    skipped += 1
                    _ssync_log("error", "db_upsert_failed", orderId=oid, orderNumber=order_number, shipmentId=ss_ship_id, error=str(e))
                    record_skipped_order(
                        execute_db,
                        str(oid),
                        order_number,
                        o.get("orderDate"),
                        "db_upsert_failed",
                        {"error": str(e), "shipmentId": ss_ship_id, "orderId": oid, "orderNumber": order_number},
                    )
                    order_failed = True
                    break

                # Cancellation check inside per-shipment loop
                if callable(should_cancel_fn) and should_cancel_fn():
                    msg = f"Sync canceled by user after {synced} synced, {skipped} skipped"
                    if progress_callback:
                        progress_callback(synced=synced, skipped=skipped, current_page=page,
                                          status='completed', message=msg)
                    return True, msg

                # Create device_distribution_records for each SKU/Lot pair in this shipment
                try:
                    for sku, qty in shipment_sku_map.items():
                        lot = sku_lot_map.get(sku) or "UNKNOWN"
                        raw_payload = {
                            "Facility Name": facility,
                            "Company Key": company_key,
                            "Address1": addr1,
                            "Address2": addr2,
                            "City": city,
                            "State": state,
                            "Zip": postal,
                            "SKU": sku,
                            "Lot": lot,
                            "Quantity": qty,
                            "Distribution Date": (ship_date or "")[:10],
                            "Order Number": order_number,
                            "Shipment ID": ss_ship_id,
                        }

                        # Normalize fields using canonical schema if available
                        if _normalize_fields_json_fn:
                            payload = _normalize_fields_json_fn(raw_payload, source="shipstation")
                        else:
                            payload = raw_payload  # Fallback if normalization not set

                        execute_db(
                            "INSERT INTO device_distribution_records (rep_id, dist_id, fields_json, stored_filename, original_filename, uploaded_at, missing_required_json, unexpected_fields_json, customer_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                chosen_rep_id,
                                dist_id,
                                json.dumps(payload),
                                f"SS_{order_number}",
                                "SHIPSTATION",
                                datetime.now(),
                                json.dumps({}),
                                json.dumps({}),
                                customer_id,
                            ),
                        )
                except Exception as e:
                    skipped += 1
                    _ssync_log("error", "line_item_insert_failed", orderId=oid, orderNumber=order_number, shipmentId=ss_ship_id, error=str(e))
                    record_skipped_order(
                        execute_db,
                        str(oid),
                        order_number,
                        o.get("orderDate"),
                        "line_item_insert_failed",
                        {"error": str(e), "shipmentId": ss_ship_id, "orderId": oid, "orderNumber": order_number},
                    )
                    order_failed = True
                    break

                # Upsert to new_customer_records entry (per shipment)
                customer_fields = {
                    "Facility Name": facility,
                    "Address1": addr1,
                    "Address2": addr2,
                    "City": city,
                    "State": state,
                    "Zip": postal,
                    "Order Number": order_number,
                    "Ship Date": (ship_date or "")[:10],
                    "Shipment ID": ss_ship_id,
                    "Total SKUs": len(shipment_sku_map),
                    "Total Units": sum(shipment_sku_map.values()),
                }
                try:
                    existing_ncr = query_db("SELECT id FROM new_customer_records WHERE dist_id=%s", (dist_id,), one=True)
                    if existing_ncr:
                        execute_db(
                            "UPDATE new_customer_records SET uploaded_at=%s, fields_json=%s, company_key=%s, customer_id=%s WHERE id=%s",
                            (datetime.now(), json.dumps(customer_fields), company_key, customer_id, existing_ncr["id"]),
                        )
                    else:
                        execute_db(
                            "INSERT INTO new_customer_records (rep_id, dist_id, stored_filename, original_filename, uploaded_at, fields_json, company_key, customer_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                chosen_rep_id,
                                dist_id,
                                f"SS_{order_number}",
                                "ShipStation Sync",
                                datetime.now(),
                                json.dumps(customer_fields),
                                company_key,
                                customer_id,
                            ),
                        )
                except Exception as e:
                    skipped += 1
                    _ssync_log("error", "new_customer_record_upsert_failed", orderId=oid, orderNumber=order_number, shipmentId=ss_ship_id, error=str(e))
                    record_skipped_order(
                        execute_db,
                        str(oid),
                        order_number,
                        o.get("orderDate"),
                        "new_customer_record_upsert_failed",
                        {"error": str(e), "shipmentId": ss_ship_id, "orderId": oid, "orderNumber": order_number},
                    )
                    order_failed = True
                    break

                synced += 1
                # Log milestone every 10 synced shipments
                if synced % 10 == 0:
                    _ssync_log("info", "sync_milestone", synced=synced, skipped=skipped, 
                              orders_seen=orders_seen, shipments_seen=shipments_seen,
                              elapsed_seconds=int(time.time() - start_time))
                
                # Heartbeat: Update progress after each synced shipment (ensures progress visible)
                if progress_callback:
                    elapsed = int(time.time() - start_time)
                    progress_callback(synced=synced, skipped=skipped, current_page=page,
                                    status='running',
                                    message=f'Synced shipment {synced} (Orders: {orders_seen}, Shipments: {shipments_seen}, Skipped: {skipped}, Elapsed: {elapsed}s)')

            if order_failed:
                # Keep going; this order has been recorded as skipped.
                continue

        # Page-level throttle to avoid API timeouts/rate limits
        if throttle_seconds:
            if progress_callback:
                elapsed = int(time.time() - start_time)
                progress_callback(synced=synced, skipped=skipped, current_page=page,
                                  status='running', 
                                  message=f'Waiting {throttle_seconds}s before next page... (Synced: {synced}, Skipped: {skipped}, Orders: {orders_seen}, Shipments: {shipments_seen}, Elapsed: {elapsed}s)')
            time.sleep(throttle_seconds)

    elapsed = int(time.time() - start_time)
    if synced == 0 and skipped > 0:
        msg = f"All orders already synced ({skipped} checked of {orders_seen} in {elapsed}s; shipments {shipments_seen})"
    else:
        msg = f"Synced {synced} shipments, {skipped} orders skipped (checked {orders_seen} orders, {shipments_seen} shipments, {elapsed}s)"

    # Final logging milestone
    _ssync_log("info", "sync_completed", synced=synced, skipped=skipped, 
              orders_seen=orders_seen, shipments_seen=shipments_seen, 
              elapsed_seconds=elapsed, message=msg)

    # Store lightweight summary for dashboard display
    record_sync_run(execute_db, msg, synced, skipped, orders_seen, shipments_seen, elapsed)
    
    if progress_callback:
        progress_callback(synced=synced, skipped=skipped, current_page=page,
                        status='completed', message=msg)
    return True, msg

def deep_rescan_since_2024(api_key: str, api_secret: str, default_rep_id: int, query_db, execute_db, progress_callback=None, should_cancel_fn=None):
    """
    Archive existing ShipStation-sourced data, then perform a full rebuild from 2024-01-01.
    Archives are stored in *_archive tables (created if missing) with a timestamp marker.
    
    Uses explicit column lists to prevent schema drift issues when columns are added via ALTER TABLE.
    """
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure archive tables exist with explicit column definitions
    # This prevents schema drift when source tables have columns added via ALTER TABLE
    execute_db("""
        CREATE TABLE IF NOT EXISTS devices_distributed_archive (
            id SERIAL PRIMARY KEY,
            rep_id INTEGER NOT NULL,
            shipment_id INTEGER,
            created_at TEXT NOT NULL,
            order_number TEXT,
            ship_date TEXT,
            tracking_number TEXT,
            source TEXT DEFAULT 'manual',
            distribution_number TEXT,
            ss_shipment_id TEXT,
            customer_id INTEGER
        );
    """)
    execute_db("""
        CREATE TABLE IF NOT EXISTS device_distribution_records_archive (
            id SERIAL PRIMARY KEY,
            rep_id INTEGER NOT NULL,
            dist_id INTEGER NOT NULL,
            stored_filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            fields_json TEXT NOT NULL,
            missing_required_json TEXT,
            unexpected_fields_json TEXT,
            customer_id INTEGER
        );
    """)
    execute_db("""
        CREATE TABLE IF NOT EXISTS new_customer_records_archive (
            id SERIAL PRIMARY KEY,
            rep_id INTEGER,
            dist_id INTEGER,
            stored_filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            fields_json TEXT NOT NULL,
            company_key TEXT,
            customer_id INTEGER
        );
    """)
    
    # Add missing columns to archive tables if they exist in source tables (handles schema drift)
    # This allows graceful handling if new columns are added after archive table creation
    try:
        execute_db("ALTER TABLE devices_distributed_archive ADD COLUMN IF NOT EXISTS distribution_number TEXT")
        execute_db("ALTER TABLE devices_distributed_archive ADD COLUMN IF NOT EXISTS ss_shipment_id TEXT")
        execute_db("ALTER TABLE devices_distributed_archive ADD COLUMN IF NOT EXISTS customer_id INTEGER")
    except Exception:
        pass  # Columns may already exist
    
    try:
        execute_db("ALTER TABLE device_distribution_records_archive ADD COLUMN IF NOT EXISTS missing_required_json TEXT")
        execute_db("ALTER TABLE device_distribution_records_archive ADD COLUMN IF NOT EXISTS unexpected_fields_json TEXT")
        execute_db("ALTER TABLE device_distribution_records_archive ADD COLUMN IF NOT EXISTS customer_id INTEGER")
    except Exception:
        pass
    
    try:
        execute_db("ALTER TABLE new_customer_records_archive ADD COLUMN IF NOT EXISTS customer_id INTEGER")
    except Exception:
        pass
    
    # Archive current ShipStation data using explicit column lists (prevents column mismatch errors)
    try:
        execute_db("""
            INSERT INTO devices_distributed_archive 
            (id, rep_id, shipment_id, created_at, order_number, ship_date, tracking_number, source, distribution_number, ss_shipment_id, customer_id)
            SELECT id, rep_id, shipment_id, created_at, order_number, ship_date, tracking_number, source, distribution_number, ss_shipment_id, customer_id
            FROM devices_distributed 
            WHERE LOWER(TRIM(COALESCE(source,'')))='shipstation'
            ON CONFLICT (id) DO NOTHING
        """)
    except Exception as e:
        error_msg = f"Failed to archive devices_distributed: {str(e)}. This may indicate a schema mismatch between source and archive tables."
        if progress_callback:
            progress_callback(synced=0, skipped=0, current_page=0, status='error', message=error_msg)
        raise RuntimeError(error_msg) from e
    
    try:
        execute_db("""
            INSERT INTO device_distribution_records_archive
            (id, rep_id, dist_id, stored_filename, original_filename, uploaded_at, fields_json, missing_required_json, unexpected_fields_json, customer_id)
            SELECT ddr.id, ddr.rep_id, ddr.dist_id, ddr.stored_filename, ddr.original_filename, ddr.uploaded_at, 
                   ddr.fields_json, ddr.missing_required_json, ddr.unexpected_fields_json, ddr.customer_id
            FROM device_distribution_records ddr 
            JOIN devices_distributed dd ON dd.id=ddr.dist_id
            WHERE LOWER(TRIM(COALESCE(dd.source,'')))='shipstation'
            ON CONFLICT (id) DO NOTHING
        """)
    except Exception as e:
        error_msg = f"Failed to archive device_distribution_records: {str(e)}. This may indicate a schema mismatch between source and archive tables."
        if progress_callback:
            progress_callback(synced=0, skipped=0, current_page=0, status='error', message=error_msg)
        raise RuntimeError(error_msg) from e
    
    try:
        execute_db("""
            INSERT INTO new_customer_records_archive
            (id, rep_id, dist_id, stored_filename, original_filename, uploaded_at, fields_json, company_key, customer_id)
            SELECT ncr.id, ncr.rep_id, ncr.dist_id, ncr.stored_filename, ncr.original_filename, ncr.uploaded_at, 
                   ncr.fields_json, ncr.company_key, ncr.customer_id
            FROM new_customer_records ncr 
            JOIN devices_distributed dd ON dd.id=ncr.dist_id
            WHERE LOWER(TRIM(COALESCE(dd.source,'')))='shipstation'
            ON CONFLICT (id) DO NOTHING
        """)
    except Exception as e:
        error_msg = f"Failed to archive new_customer_records: {str(e)}. This may indicate a schema mismatch between source and archive tables."
        if progress_callback:
            progress_callback(synced=0, skipped=0, current_page=0, status='error', message=error_msg)
        raise RuntimeError(error_msg) from e
    # Delete current ShipStation data (children before parents)
    execute_db("DELETE FROM device_distribution_records WHERE dist_id IN (SELECT id FROM devices_distributed WHERE LOWER(TRIM(COALESCE(source,'')))='shipstation')")
    execute_db("DELETE FROM new_customer_records WHERE dist_id IN (SELECT id FROM devices_distributed WHERE LOWER(TRIM(COALESCE(source,'')))='shipstation')")
    execute_db("DELETE FROM devices_distributed WHERE LOWER(TRIM(COALESCE(source,'')))='shipstation'")
    # Perform full rescan starting 2024-01-01
    return sync_units_and_grouping(api_key, api_secret, default_rep_id, query_db, execute_db,
                                   start_date_override='2024-01-01', max_orders=100000, force_rescan=False,
                                   progress_callback=progress_callback, throttle_seconds=30,
                                   should_cancel_fn=should_cancel_fn)