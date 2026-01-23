#!/usr/bin/env python3
"""
Production startup script for DigitalOcean App Platform.

1. Runs migrations + seed (release.py)
2. Starts gunicorn (replaces this process via exec)

Usage (in DO Run Command):
    python scripts/start.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    # Step 1: Run release (migrations + seed)
    print("=== Running release phase ===", flush=True)
    from scripts.release import run_release
    try:
        run_release()
    except Exception as e:
        print(f"Release failed: {e}", flush=True)
        sys.exit(1)

    # Step 2: Start gunicorn (exec replaces this process)
    port = os.environ.get("PORT", "8080")
    print(f"=== Starting gunicorn on port {port} ===", flush=True)

    # Use exec to replace the Python process with gunicorn
    # This ensures gunicorn is PID 1 and handles signals correctly
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "app.wsgi:app",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "2",
            "--timeout", "60",
            "--preload",
            "--access-logfile", "-",
            "--error-logfile", "-",
        ],
    )


if __name__ == "__main__":
    main()
