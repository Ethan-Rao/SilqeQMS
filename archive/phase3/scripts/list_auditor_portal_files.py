"""Generate a CSV listing of every document visible to the auditor in the
Auditor Files portal.

This walks the on-disk "Auditor Files/" tree with the same filters the
portal uses in ``app.eqms.modules.auditor_portal.fs``:

* Skip dot-prefixed names (hidden files, e.g. ``.gitkeep``).
* Skip ``~$*`` Office lock files.

It emits a CSV at docs/auditor_portal_file_list.csv with these columns,
sorted by (top-level folder, full path, all case-insensitive):

    Path                : full relative path under "Auditor Files/"
                          (POSIX slashes so Excel and file explorers are happy).
    Top-Level Folder    : first path segment (e.g. "QM Documents").
    Parent Folder       : relative path of the immediate parent, empty if
                          the file sits directly in a top-level folder.
    Depth               : number of subfolder levels below a top-level
                          folder (0 = directly inside it).
    Filename            : leaf name of the file.
    Type                : friendly label derived from the extension
                          (PDF / Word / Excel / CSV / Text / Image / File).
                          Mirrors the mapping used by folder.html.
    Size (KB)           : rounded-up KB (matches what Windows Explorer shows).

Run from repo root:

    python scripts/list_auditor_portal_files.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDITOR_ROOT = REPO_ROOT / "Auditor Files"
OUT_CSV = REPO_ROOT / "docs" / "auditor_portal_file_list.csv"

TYPE_MAP = {
    "pdf": "PDF",
    "docx": "Word",
    "doc": "Word",
    "xlsx": "Excel",
    "xls": "Excel",
    "csv": "CSV",
    "txt": "Text",
    "png": "Image",
    "jpg": "Image",
    "jpeg": "Image",
    "gif": "Image",
}


def is_skipped(name: str) -> bool:
    return name.startswith(".") or name.startswith("~$")


def type_label(filename: str) -> str:
    if "." not in filename:
        return "File"
    ext = filename.rsplit(".", 1)[1].lower()
    return TYPE_MAP.get(ext, "File")


def iter_files(root: Path):
    """Yield Path objects for every non-skipped file under root, recursively."""
    stack: list[Path] = [root]
    while stack:
        folder = stack.pop()
        try:
            children = list(folder.iterdir())
        except OSError:
            continue
        for child in children:
            if is_skipped(child.name):
                continue
            try:
                if child.is_dir():
                    stack.append(child)
                elif child.is_file():
                    yield child
            except OSError:
                continue


def main() -> int:
    if not AUDITOR_ROOT.is_dir():
        print(f"ERROR: {AUDITOR_ROOT} is not a directory.")
        return 1

    rows: list[dict[str, str | int]] = []
    for path in iter_files(AUDITOR_ROOT):
        rel = path.relative_to(AUDITOR_ROOT)
        parts = rel.parts  # e.g. ("QM Documents", "sub", "file.pdf")
        top = parts[0] if len(parts) >= 1 else ""
        parent_parts = parts[:-1]
        parent_rel = "/".join(parent_parts)
        depth = max(0, len(parent_parts) - 1)  # 0 = direct child of top-level
        try:
            size_bytes = path.stat().st_size
        except OSError:
            size_bytes = 0
        size_kb = max(1, math.ceil(size_bytes / 1024)) if size_bytes else 0
        rows.append({
            "Path": str(rel).replace("\\", "/"),
            "Top-Level Folder": top,
            "Parent Folder": parent_rel,
            "Depth": depth,
            "Filename": path.name,
            "Type": type_label(path.name),
            "Size (KB)": size_kb,
        })

    rows.sort(key=lambda r: (str(r["Top-Level Folder"]).lower(), str(r["Path"]).lower()))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["Path", "Top-Level Folder", "Parent Folder", "Depth", "Filename", "Type", "Size (KB)"]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_CSV.relative_to(REPO_ROOT)}")

    type_counts: dict[str, int] = {}
    top_counts: dict[str, int] = {}
    for r in rows:
        type_counts[str(r["Type"])] = type_counts.get(str(r["Type"]), 0) + 1
        top_counts[str(r["Top-Level Folder"])] = top_counts.get(str(r["Top-Level Folder"]), 0) + 1
    print("\nBy type:")
    for k, v in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<6} {v}")
    print("\nBy top-level folder (count desc — matches dashboard order):")
    for k, v in sorted(top_counts.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        print(f"  {v:>4}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
