"""
Migration-chain pre-ship guard (Phase 3 Prompt 5 / E1 follow-up).

The rest of the suite creates schema via ``Base.metadata.create_all``, which does
NOT execute Alembic migrations — so it cannot catch chain problems like a second
migration re-creating an index/table that an ancestor already created (which is
exactly what would fail ``alembic upgrade head`` on the production Postgres).

This test walks the real Alembic chain (authoritative ordering + head count) and
statically simulates create/drop of indexes and tables to surface duplicates
locally, without needing a database. CI additionally runs a real
``alembic upgrade head`` against a clean Postgres (see .github/workflows/ci.yml).
"""
from __future__ import annotations

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]

# Match both op.* and batch_op.* forms.
_CREATE_INDEX = re.compile(r"""\.create_index\(\s*['"]([^'"]+)['"]""")
_DROP_INDEX = re.compile(r"""\.drop_index\(\s*['"]([^'"]+)['"]""")
_CREATE_TABLE = re.compile(r"""op\.create_table\(\s*['"]([^'"]+)['"]""")
_DROP_TABLE = re.compile(r"""op\.drop_table\(\s*['"]([^'"]+)['"]""")

# Markers that a migration guards its DDL with runtime introspection (idempotent
# / dialect-branched), so a "create" there won't blindly fail if the object
# exists. Such creates are never treated as unconditional duplicates.
_GUARD_MARKERS = ("inspect(", "get_indexes", "has_index", "if_not_exists", "has_table")


def _ordered_revisions() -> list:
    cfg = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected a single Alembic head, found {len(heads)}: {heads}"
    # walk_revisions yields head -> base; reverse to apply in upgrade order.
    revs = list(script.walk_revisions("base", "heads"))
    revs.reverse()
    return revs


def _upgrade_source(rev) -> str:
    """Return only the upgrade() body source so downgrade ops don't confuse us."""
    src = Path(rev.path).read_text(encoding="utf-8")
    up = src.find("def upgrade(")
    down = src.find("def downgrade(")
    if up == -1:
        return ""
    return src[up:down] if down != -1 else src[up:]


def test_single_head():
    _ordered_revisions()  # asserts single head internally


def _events(body: str):
    """Yield (position, kind, name) DDL events in source order."""
    for kind, rx in (("create_index", _CREATE_INDEX), ("drop_index", _DROP_INDEX),
                     ("create_table", _CREATE_TABLE), ("drop_table", _DROP_TABLE)):
        for m in rx.finditer(body):
            yield (m.start(), kind, m.group(1))


def test_no_duplicate_index_or_table_creation_across_chain():
    live_indexes: dict[str, str] = {}  # name -> revision that created it
    live_tables: dict[str, str] = {}
    problems: list[str] = []

    for rev in _ordered_revisions():
        body = _upgrade_source(rev)
        guarded = any(marker in body for marker in _GUARD_MARKERS)

        for _pos, kind, name in sorted(_events(body)):
            if kind == "create_index":
                if name in live_indexes and not guarded:
                    problems.append(
                        f"index '{name}' created unconditionally in {rev.revision} but already "
                        f"created in {live_indexes[name]} (would fail alembic upgrade head)"
                    )
                live_indexes[name] = rev.revision
            elif kind == "drop_index":
                live_indexes.pop(name, None)
            elif kind == "create_table":
                if name in live_tables and not guarded:
                    problems.append(
                        f"table '{name}' created unconditionally in {rev.revision} but already "
                        f"created in {live_tables[name]}"
                    )
                live_tables[name] = rev.revision
            elif kind == "drop_table":
                live_tables.pop(name, None)

    assert not problems, "Migration chain conflicts:\n  - " + "\n  - ".join(problems)
