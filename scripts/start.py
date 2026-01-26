#!/usr/bin/env python3
"""
Production startup script for DigitalOcean App Platform.

This is the CANONICAL startup script. Use this in the DO Run Command.

1. Runs migrations + seed (release.py)
2. Starts gunicorn (replaces this process via os.execvp)

Usage (in DO Run Command):
    python scripts/start.py

Why this script exists:
- Shell command chaining (&&) is unreliable in some container environments
- os.execvp properly replaces this process with gunicorn (PID 1, signal handling)
- Single point of control for startup sequence
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    # Step 0: Validate PORT environment variable
    port = os.environ.get("PORT", "").strip()
    if not port:
        print("WARNING: PORT not set, using default 8080", flush=True)
        port = "8080"
    
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError("Port out of range")
    except ValueError:
        print(f"ERROR: Invalid PORT value '{port}'. Must be integer 1-65535.", flush=True)
        sys.exit(1)
    
    print(f"PORT={port} validated", flush=True)
    
    # Step 1: Run release (migrations + seed)
    print("=== Running release phase ===", flush=True)
    from scripts.release import run_release
    try:
        run_release()
    except Exception as e:
        print(f"Release failed: {e}", flush=True)
        sys.exit(1)

    # Step 2: Start gunicorn (exec replaces this process)
    print(f"=== Starting gunicorn ===", flush=True)
    print(f"Gunicorn binding to 0.0.0.0:{port}", flush=True)
    print(f"Health check endpoint ready at /healthz", flush=True)

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
