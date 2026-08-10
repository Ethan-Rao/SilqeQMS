"""
Temporary read-only Auditor Files portal (see docs/AUDITOR_PORTAL_OPERATOR_GUIDE.md).

Cache invalidation uses (rel_path, file size, mtime_ns). If an operator replaces a file
without changing size or mtime, cached PDFs may be stale until the blob changes.

The blueprint is loaded lazily to avoid import cycles with ``app.eqms.models`` ↔ ``audit``.
"""


def __getattr__(name: str):
    if name == "bp":
        from app.eqms.modules.auditor_portal.admin import bp as _bp

        return _bp
    raise AttributeError(name)


__all__ = ["bp"]
