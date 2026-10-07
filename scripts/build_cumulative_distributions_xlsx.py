"""Build the cumulative catheter distributions workbook for sales use.

Reads the live distribution log rather than a CSV export, and groups on
``customer_id`` rather than on facility-name text. That is the identity the
rest of the system uses, so sites no longer split across spellings the way they
did when this was built from name matching.

Units come from ``distribution_lines``, the canonical per-SKU quantity.

    python scripts/build_cumulative_distributions_xlsx.py
    python scripts/build_cumulative_distributions_xlsx.py --start 2025-01-01
"""
from __future__ import annotations

import argparse
import calendar
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from openpyxl import Workbook  # noqa: E402
from openpyxl.chart import BarChart, Reference  # noqa: E402
from openpyxl.chart.label import DataLabelList  # noqa: E402
from openpyxl.chart.legend import Legend  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

TOP_N = 25

# Presentation names, keyed on customer id, for facility names too long to read
# in a chart legend. The underlying customer records are not changed.
DISPLAY_NAME = {
    609: "Rancho Los Amigos",
    613: "Riverside County Reg'l MC",
    614: "Aspirus (Wausau)",
    616: "Loma Linda Univ Health",
    624: "University of Virginia",
    625: "Aspirus (Wisc Rapids)",
    628: "VAMC Loma Linda",
    630: "Santa Clara Valley MC",
    635: "VAMC San Diego",
    641: "Olive View UCLA",
    643: "University of Michigan",
    647: "UPMC Home Health of Central PA",
    651: "Temple University Health",
    657: "Aspirus (Rhinelander)",
    660: "Temple University (Rockledge)",
    668: "University of Michigan (Brighton)",
    673: "Tower Urology",
    677: "Temple University (Ft Washington)",
}

PALETTE = [
    "1F4E79", "2E75B6", "5B9BD5", "9DC3E6", "00B0F0",
    "548235", "70AD47", "A9D08E", "C6E0B4", "FFC000",
    "ED7D31", "F4B183", "C45911", "A02B93", "7030A0",
    "5B2C6F", "C00000", "FF5050", "833C0C", "BF8F00",
    "0070C0", "00B050", "FF6600", "44546A", "9B59B6",
    "7F7F7F",
]


def month_floor(d: date) -> date:
    return date(d.year, d.month, 1)


def month_before(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def is_month_complete(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def month_range(start: date, end: date) -> list[date]:
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def title_clean(name: str) -> str:
    return name.title() if (name.isupper() or name.islower()) else name


def load_rows(start: date):
    """(month, display_name, units) for every distribution line from `start`."""
    from app.eqms import create_app
    from app.eqms.db import db_session
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        s = db_session()
        rows = s.execute(
            text(
                """
                SELECT d.ship_date, d.customer_id, c.facility_name,
                       sum(l.quantity) AS units
                FROM distribution_lines l
                JOIN distribution_log_entries d ON d.id = l.distribution_entry_id
                JOIN customers c ON c.id = d.customer_id
                WHERE d.ship_date >= :start
                GROUP BY d.ship_date, d.customer_id, c.facility_name
                ORDER BY d.ship_date
                """
            ),
            {"start": start},
        ).all()
        last = s.execute(
            text("SELECT max(ship_date) FROM distribution_log_entries")
        ).scalar()

    out = []
    for ship_date, cid, facility, units in rows:
        out.append(
            {
                "month": month_floor(ship_date),
                "customer": DISPLAY_NAME.get(cid) or title_clean(facility or "Unknown"),
                "units": int(units or 0),
            }
        )
    return out, last


def build_matrices(rows, start: date, end: date):
    """Shipments past `end` fold into it, so the totals stay whole."""
    lifetime = defaultdict(int)
    monthly = defaultdict(lambda: defaultdict(int))
    for r in rows:
        lifetime[r["customer"]] += r["units"]
        monthly[min(r["month"], end)][r["customer"]] += r["units"]

    ranked = sorted(lifetime.items(), key=lambda kv: (-kv[1], kv[0]))
    named = [n for n, _ in ranked[:TOP_N]]
    named_set = set(named)

    months = month_range(start, end)
    cols = named + ["Other"]
    cum, running = {}, {c: 0 for c in cols}
    for m in months:
        for c, q in monthly[m].items():
            running[c if c in named_set else "Other"] += q
        cum[m] = dict(running)
    return named, months, cum, lifetime, ranked


def style_workbook(named, months, cum, out_path: Path, start: date, folded_through):
    wb = Workbook()
    ws = wb.active
    ws.title = "Cumulative by Customer"

    cols = named + ["Other"]
    headers = ["Month"] + cols
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=10)
    thin = Border(*(Side(style="thin", color="D9E2F3"),) * 4)
    alt_fill = PatternFill("solid", fgColor="F2F7FB")
    other_fill = PatternFill("solid", fgColor="FFF2CC")

    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center", vertical="bottom", wrap_text=True,
            textRotation=90 if col > 1 else 0,
        )
    ws.row_dimensions[1].height = 110

    for r_i, m in enumerate(months, 2):
        mc = ws.cell(r_i, 1, m)
        mc.number_format = "MMM-YYYY"
        mc.font = Font(name="Calibri", bold=True, size=11)
        mc.alignment = Alignment(horizontal="center")
        mc.border = thin
        if r_i % 2 == 0:
            mc.fill = alt_fill
        for c_i, cust in enumerate(cols, 2):
            cell = ws.cell(r_i, c_i, cum[m][cust])
            cell.font = Font(name="Calibri", size=10)
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin
            cell.number_format = "#,##0"
            if cust == "Other":
                cell.fill = other_fill
            elif r_i % 2 == 0:
                cell.fill = alt_fill

    ws.column_dimensions["A"].width = 12
    for i in range(2, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 3.8

    last_row = 1 + len(months)
    tot_row = last_row + 1
    ws.cell(tot_row, 1, "Total").font = Font(
        name="Calibri", bold=True, size=11, color="1F4E79")
    for c_i, cust in enumerate(cols, 2):
        cell = ws.cell(tot_row, c_i, cum[months[-1]][cust])
        cell.font = Font(name="Calibri", bold=True, size=10)
        cell.number_format = "#,##0"
        cell.alignment = Alignment(horizontal="center")
        cell.fill = PatternFill("solid", fgColor="D6EAF8")
        cell.border = thin

    note_row = tot_row + 1
    grand = sum(cum[months[-1]].values())
    through = (folded_through or months[-1]).strftime("%d %b %Y").lstrip("0")
    note = (
        f"Cumulative units shipped from {start.strftime('%d %b %Y').lstrip('0')} "
        f"through {through}. Total {grand:,} units."
    )
    if folded_through:
        note += (f" Shipments after {months[-1].strftime('%B %Y')} are included in "
                 f"the {months[-1].strftime('%b-%Y')} figure.")
    nc = ws.cell(note_row, 1, note)
    nc.font = Font(name="Calibri", italic=True, size=9, color="595959")

    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.overlap = 100
    chart.title = "Cumulative Catheter Distributions by Customer"
    chart.y_axis.title = "Cumulative Units"
    chart.x_axis.title = None
    chart.style = 10
    chart.legend = Legend()
    chart.legend.position = "b"
    chart.legend.overlay = False

    data = Reference(ws, min_col=2, min_row=1, max_col=len(headers), max_row=last_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=last_row))
    chart.width = 24
    chart.height = 14

    for series in chart.series:
        series.dLbls = DataLabelList()
        series.dLbls.showVal = False
        series.dLbls.showSerName = False
        series.dLbls.showCatName = False
        series.dLbls.showPercent = False
        series.dLbls.showLegendKey = False
    for idx, series in enumerate(chart.series):
        series.graphicalProperties.solidFill = (
            PALETTE[idx] if idx < len(PALETTE) else "7F7F7F")

    ws.add_chart(chart, f"A{note_row + 2}")
    ws.freeze_panes = "B2"
    ws.print_title_rows = "1:1"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="", help="last month to show, YYYY-MM-DD")
    args = ap.parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d").date()

    rows, last_ship = load_rows(start)
    if args.end:
        end = month_floor(datetime.strptime(args.end, "%Y-%m-%d").date())
    elif is_month_complete(last_ship):
        end = month_floor(last_ship)
    else:
        # Ending on a part-month would show a short final bar and read as a
        # drop-off. End on the last whole month and fold the stragglers in.
        end = month_before(month_floor(last_ship))
    folded = last_ship if month_floor(last_ship) > end else None

    named, months, cum, lifetime, ranked = build_matrices(rows, start, end)

    stamp = date.today().strftime("%Y%m%d")
    name = f"catheter_distributions_cumulative_by_customer_{stamp}.xlsx"
    primary = ROOT / "working-files" / "data-exports" / name
    style_workbook(named, months, cum, primary, start, folded)
    shutil.copy2(primary, ROOT / name)

    print(f"Wrote {primary}")
    print(f"  copy  {ROOT / name}")
    print(f"Window: {months[0]} .. {months[-1]} ({len(months)} months)")
    if folded:
        print(f"  note: shipments through {folded} folded into "
              f"{months[-1].strftime('%b-%Y')}")
    print(f"Distribution line-groups used: {len(rows)}")
    print(f"\nTop {TOP_N} by units since {start}:")
    for i, c in enumerate(named, 1):
        print(f"  {i:2d}. {c:38s} {lifetime[c]:6,d}")
    other = sum(v for k, v in lifetime.items() if k not in set(named))
    print(f"      {'Other (' + str(len(lifetime) - len(named)) + ' customers)':38s} {other:6,d}")
    print(f"\nGrand total: {sum(lifetime.values()):,} units "
          f"across {len(lifetime)} customers")


if __name__ == "__main__":
    main()
