"""Gunicorn hooks for App Platform.

Bind first, then run one-shot P4-08B file import in the master. start.py used to
run that import during release, which held port 8080 closed until DigitalOcean
readiness failed (connection refused on /healthz).
"""


def when_ready(server):
    try:
        from scripts.release import run_file_import_after_listen

        run_file_import_after_listen()
    except Exception as exc:
        print(f"P4-08B file import skipped: {type(exc).__name__}.", flush=True)
    try:
        from scripts.attach_invoice_pdfs import run_on_listen

        run_on_listen()
    except Exception as exc:
        print(f"Invoice PDF upload skipped: {type(exc).__name__}.", flush=True)
