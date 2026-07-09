"""Clean-checkout import guard (Prompt 6 Task C).

Exports the *committed* tree (``git archive HEAD``) into a throwaway directory
and runs ``python -c "import app.wsgi"`` from there. This catches the class of
bug where committed code depends on a symbol whose definition was left
uncommitted (e.g. a caller importing ``merge_import_metadata`` that only exists
in an unstaged file) — the local working tree imports fine, but a fresh
production checkout of committed code fails at import time.

Run locally before pushing, or in CI. Exits non-zero if the import fails.

    python scripts/check_clean_import.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="silq-import-guard-") as td:
        tmp = Path(td)
        archive = tmp / "committed.tar"
        tree = tmp / "tree"
        tree.mkdir()

        # Export exactly what is committed at HEAD (excludes uncommitted files).
        subprocess.run(
            ["git", "archive", "HEAD", "-o", str(archive)],
            cwd=str(_ROOT),
            check=True,
        )
        with tarfile.open(archive) as tf:
            # Python 3.12+ accepts a filter; older versions do not.
            if sys.version_info >= (3, 12):
                tf.extractall(tree, filter="data")
            else:
                tf.extractall(tree)

        # Minimal, side-effect-free environment: local storage + a throwaway
        # SQLite DB so create_app() can construct without external services.
        env = dict(os.environ)
        env.update(
            ENV="ci",
            SECRET_KEY="import-guard",
            STORAGE_BACKEND="local",
            STORAGE_LOCAL_ROOT=str(tmp / "storage"),
            DATABASE_URL=f"sqlite:///{(tmp / 'guard.db').as_posix()}",
        )
        for key in ("S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID",
                    "S3_SECRET_ACCESS_KEY", "S3_REGION"):
            env.pop(key, None)

        print(f"[import-guard] importing app.wsgi from clean tree: {tree}")
        result = subprocess.run(
            [sys.executable, "-c", "import app.wsgi"],
            cwd=str(tree),
            env=env,
        )

    if result.returncode != 0:
        print("[import-guard] FAILED: committed tree cannot `import app.wsgi`.",
              file=sys.stderr)
        return result.returncode
    print("[import-guard] OK: committed tree imports cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
