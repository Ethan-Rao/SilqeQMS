"""
REP Traceability (P0) module.

Scope (P0):
- Distribution Log (manual entry, CSV import/export, edit/delete)
- Tracing Reports (generate CSV artifacts, store immutably, download)
- Approval Evidence (.eml upload + download, minimal header parsing)

Hard constraints:
- No rep pages; everything lives under /admin/*
- No email sending
"""

