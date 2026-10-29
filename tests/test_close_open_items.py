"""DHR folder fallback, download label, and stale ShipStation skip rows."""
from pathlib import Path

from app.eqms.modules.manufacturing.admin import (
    cleartract_lot_folder_names,
    cleartract_parent_folder_names,
    resolve_cleartract_dhr_folder,
)
from app.eqms.modules.shipstation_sync.admin import no_valid_items_hidden

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "eqms" / "templates" / "admin" / "manufacturing" / "index.html"


class _Folder:
    def __init__(self, folder_id, name, parent_id=None):
        self.id = folder_id
        self.name = name
        self.parent_id = parent_id


def _finder(folders):
    by_parent: dict = {}
    for folder in folders:
        by_parent.setdefault(folder.parent_id, []).append(folder)

    def find_child(parent_id, *names):
        wanted = {n.lower() for n in names}
        for folder in by_parent.get(parent_id, []):
            if folder.name.lower() in wanted:
                return folder
        return None

    return find_child


def test_parent_folders_keep_dhrs_name_and_the_older_name():
    assert cleartract_parent_folder_names("SLQ-211810SPT") == (
        "SLQ-211810SPT DHRs",
        "SLQ-211810SPT",
    )


def test_lot_folder_alias_for_14_fr():
    assert cleartract_lot_folder_names("SLQ-11192024") == (
        "LotSLQ-11192024",
        "LotSLQ-1192024",
    )


def test_lookup_uses_folder_without_dhrs_suffix():
    root = _Folder(1, "ClearTract Foley Catheters")
    parent = _Folder(2, "SLQ-211810SPT", root.id)
    lot = _Folder(3, "LotSLQ-81020515241", parent.id)
    found = resolve_cleartract_dhr_folder(
        _finder([root, parent, lot]), root.id, "SLQ-211810SPT", "SLQ-81020515241"
    )
    assert found is lot


def test_lookup_uses_renamed_14_fr_folder():
    root = _Folder(1, "ClearTract Foley Catheters")
    parent = _Folder(2, "SLQ-211410SPT", root.id)
    lot = _Folder(3, "LotSLQ-1192024", parent.id)
    found = resolve_cleartract_dhr_folder(
        _finder([root, parent, lot]), root.id, "SLQ-211410SPT", "SLQ-11192024"
    )
    assert found is lot


def test_download_label_and_dark_row():
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("{% macro doc_panel_files")
    end = text.index("{%- endmacro %}", start)
    macro = text[start:end]
    assert ">Download</a>" in macro
    assert ">↓</a>" not in macro
    assert "#f8f9fa" not in text
    assert "var(--panel)" in text


def test_skip_row_hidden_when_distribution_exists():
    assert no_valid_items_hidden("no_valid_items", "SO 0000433", {"433"})
    assert not no_valid_items_hidden("no_valid_items", "SO 0000999", {"433"})
    assert not no_valid_items_hidden("no_shipments", "SO 0000433", {"433"})
