"""Attach the Distribution/ source PDFs to the live sales orders and distributions.

Sales order pages are attached to their sales order; packing slip pages are
attached to the distributions they document. Pages are extracted individually so
each record carries only its own evidence, matching how the bulk importer stores
``sales_order_page`` and ``packing_slip`` attachments.

Idempotent: an order or distribution that already has an attachment of that type
with the same storage key is left alone.

    python scripts/dist_upload_source_pdfs.py            # dry run
    python scripts/dist_upload_source_pdfs.py --execute
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# Distribution/ is a local-only working folder and is gitignored, so on App
# Platform the same PDFs are read from the committed import corpora instead.
SOURCE_DIRS = [
    ROOT / "Distribution",
    ROOT / "scripts" / "_dist_oct2026_import_files",
    ROOT / "scripts" / "_p4_08b_import_files",
]
LOG = ROOT / "_dist_upload_log.txt"


def find_source(name: str) -> Path | None:
    for d in SOURCE_DIRS:
        p = d / name
        if p.exists():
            return p
    return None


def find_data(name: str) -> Path:
    for d in [ROOT] + SOURCE_DIRS:
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(f"{name} not found in {[str(d) for d in SOURCE_DIRS]}")

out: list[str] = []


def say(m: str = "") -> None:
    print(m)
    out.append(m)


def extract_page(src: Path, page_no: int, cache: dict) -> bytes:
    """One-page PDF for a 1-based page number."""
    from pypdf import PdfReader, PdfWriter

    reader = cache.get(src)
    if reader is None:
        reader = PdfReader(str(src))
        cache[src] = reader
    w = PdfWriter()
    w.add_page(reader.pages[page_no - 1])
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _storage_writable(app) -> bool:
    from app.eqms.storage import storage_from_config

    try:
        st = storage_from_config(app.config)
        key = "tmp/dist_oct2026_put_probe.txt"
        st.put_bytes(key, b"probe", content_type="text/plain")
        st.delete(key)
        return True
    except Exception:
        return False


def run_on_release() -> None:
    """Idempotent attachment upload for App Platform release. Never raises."""
    if find_source("AugSep26SalesOrders.pdf") is None:
        print("Oct-2026 attachment upload skipped: import files not in image.", flush=True)
        return
    try:
        _run(dry=False, only={"so", "ps"})
    except Exception as exc:
        print(
            f"Oct-2026 attachment upload skipped: {type(exc).__name__}: {exc}",
            flush=True,
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--only", default="so,ps", help="so and/or ps")
    args = ap.parse_args()
    _run(dry=not args.execute, only={t.strip().lower() for t in args.only.split(",") if t.strip()})


def _run(*, dry: bool, only: set[str]) -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    from flask import current_app

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.rep_traceability.models import (
        DistributionLogEntry,
        OrderPdfAttachment,
        SalesOrder,
    )
    from app.eqms.modules.rep_traceability.service import (
        find_sales_order_by_normalized_number,
    )
    from app.eqms.storage import storage_from_config

    so_pages = json.loads(
        find_data("_dist_parsed_sales_orders.json").read_text(encoding="utf-8")
    )
    slips = json.loads(
        find_data("_dist_parsed_packing_slips.json").read_text(encoding="utf-8")
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )
        storage = storage_from_config(current_app.config)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        cache: dict = {}

        say("=" * 90)
        say(f"UPLOAD SOURCE PDFS  mode={'DRY RUN' if dry else 'EXECUTE'}  actor={actor.email}")
        say("=" * 90)

        if not dry and not _storage_writable(app):
            say("\nSKIPPED: object storage is not writable with the current credentials.")
            s.rollback()
            return

        # ------------------------------------------------------------ sales orders
        if "so" in only:
            say("\n[SO] SALES ORDER PAGES")
            # Best page per order: prefer one that parsed device lines.
            best: dict[str, dict] = {}
            for o in so_pages:
                num = o.get("order_number")
                if not num:
                    continue
                prev = best.get(num)
                if prev is None or (o.get("device_units") or 0) > (prev.get("device_units") or 0):
                    best[num] = o
            done = skip = miss = 0
            for num, o in sorted(best.items()):
                so = find_sales_order_by_normalized_number(s, num)
                if not so:
                    continue
                src = find_source(o["source_pdf"])
                if src is None:
                    say(f"  {num}: SKIP source missing {o['source_pdf']}")
                    miss += 1
                    continue
                existing = (
                    s.query(OrderPdfAttachment)
                    .filter(
                        OrderPdfAttachment.sales_order_id == so.id,
                        OrderPdfAttachment.pdf_type.in_(
                            ("sales_order", "sales_order_page", "manual_upload")
                        ),
                    )
                    .first()
                )
                if existing:
                    skip += 1
                    continue
                key = f"sales_orders/{num}/pdfs/reconciliation_{stamp}_SO_{num}.pdf"
                say(f"  {num}: ATTACH {o['source_pdf']}#p{o['page']} -> {key}")
                if not dry:
                    data = extract_page(src, o["page"], cache)
                    storage.put_bytes(key, data, content_type="application/pdf")
                    s.add(
                        OrderPdfAttachment(
                            sales_order_id=so.id,
                            distribution_entry_id=None,
                            storage_key=key,
                            filename=f"SO_{num}.pdf",
                            pdf_type="sales_order_page",
                            content_type="application/pdf",
                            size_bytes=len(data),
                            uploaded_by_user_id=actor.id,
                        )
                    )
                    record_event(
                        s, actor=actor, action="sales_order.attachment_uploaded",
                        entity_type="sales_order", entity_id=num,
                        reason="Distribution reconciliation Oct-2026: source document attached",
                        metadata={
                            "source_pdf": o["source_pdf"], "source_page": o["page"],
                            "storage_key": key, "pdf_type": "sales_order_page",
                        },
                    )
                    s.flush()
                done += 1
            say(f"  -> {done} attached, {skip} already had one, {miss} source missing")

        # ------------------------------------------------------------ packing slips
        if "ps" in only:
            say("\n[PS] PACKING SLIP PAGES")
            # Distributions grouped by normalized order number.
            dists: dict[str, list] = defaultdict(list)
            for d in s.query(DistributionLogEntry).all():
                num = "".join(c for c in (d.order_number or "") if c.isdigit()).zfill(7)
                dists[num].append(d)

            # One slip per (order, ship_date, content); prefer the earliest export.
            chosen: dict[tuple, dict] = {}
            for sl in slips:
                if not sl.get("order_number"):
                    continue
                num = sl["order_number"].upper().replace("SO", "").strip().zfill(7)
                k = (num, sl.get("ship_date"), sl.get("slip_on_page"))
                if k not in chosen:
                    chosen[k] = sl

            done = skip = miss = nolink = 0
            for (num, ship_date, _), sl in sorted(chosen.items()):
                targets = dists.get(num) or []
                if not targets:
                    nolink += 1
                    continue
                src = find_source(sl["source_pdf"])
                if src is None:
                    miss += 1
                    continue
                # Attach to the distribution whose ship date matches the slip.
                def same_day(d) -> bool:
                    if not (ship_date and d.ship_date):
                        return False
                    try:
                        m, day, y = (int(p) for p in ship_date.split("/"))
                    except ValueError:
                        return False
                    if y < 100:
                        y += 2000
                    return (d.ship_date.month, d.ship_date.day, d.ship_date.year) == (m, day, y)

                match = [d for d in targets if same_day(d)] or targets
                for d in match:
                    has = (
                        s.query(OrderPdfAttachment)
                        .filter(
                            OrderPdfAttachment.distribution_entry_id == d.id,
                            OrderPdfAttachment.pdf_type.in_(
                                ("packing_slip", "packing_slip_page")
                            ),
                        )
                        .first()
                    )
                    if has:
                        skip += 1
                        continue
                    key = (
                        f"distributions/{d.id}/pdfs/reconciliation_{stamp}"
                        f"_PS_{num}_p{sl['page']}_{sl.get('slip_on_page') or 1}.pdf"
                    )
                    say(
                        f"  dist {d.id} order {num} {d.ship_date}: ATTACH "
                        f"{sl['source_pdf']}#p{sl['page']}.{sl.get('slip_on_page')} -> {key}"
                    )
                    if not dry:
                        data = extract_page(src, sl["page"], cache)
                        storage.put_bytes(key, data, content_type="application/pdf")
                        s.add(
                            OrderPdfAttachment(
                                sales_order_id=d.sales_order_id,
                                distribution_entry_id=d.id,
                                storage_key=key,
                                filename=f"PackingSlip_{num}.pdf",
                                pdf_type="packing_slip",
                                content_type="application/pdf",
                                size_bytes=len(data),
                                uploaded_by_user_id=actor.id,
                            )
                        )
                        record_event(
                            s, actor=actor,
                            action="distribution_log_entry.upload_packing_slip",
                            entity_type="distribution_log_entry", entity_id=str(d.id),
                            reason="Distribution reconciliation Oct-2026: "
                                   "source document attached",
                            metadata={
                                "source_pdf": sl["source_pdf"], "source_page": sl["page"],
                                "slip_on_page": sl.get("slip_on_page"),
                                "order_number": num, "storage_key": key,
                            },
                        )
                        s.flush()
                    done += 1
            say(
                f"  -> {done} attached, {skip} already had one, "
                f"{miss} source missing, {nolink} slips with no distribution"
            )

        if dry:
            s.rollback()
            say("\nDRY RUN - nothing written.")
        else:
            s.commit()
            say("\nCOMMITTED.")

    LOG.write_text("\n".join(out), encoding="utf-8")
    print(f"\nlog -> {LOG}")


if __name__ == "__main__":
    main()
