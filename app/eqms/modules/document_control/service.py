from __future__ import annotations

import hashlib
import re
from datetime import date

from werkzeug.utils import secure_filename

from app.eqms.utils import utcnow


def normalize_doc_number(doc_number: str) -> str:
    return (doc_number or "").strip()


def next_revision(current: str) -> str:
    """
    Increment revision identifiers.

    Supports:
    - integers: "0" -> "1"
    - letters: "A" -> "B", "Z" -> "AA"
    - alphanumeric suffixes are not supported (kept intentionally strict for v1)
    """
    cur = (current or "").strip().upper()
    if not cur:
        return "A"

    if re.fullmatch(r"\d+", cur):
        return str(int(cur) + 1)

    if not re.fullmatch(r"[A-Z]+", cur):
        raise ValueError(f"Unsupported revision format: {current!r}")

    # Base-26 increment, A=1 ... Z=26 (Excel-style)
    n = 0
    for ch in cur:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    n += 1
    out = []
    while n > 0:
        n -= 1
        out.append(chr(ord("A") + (n % 26)))
        n //= 26
    return "".join(reversed(out))


def parse_effective_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    # HTML <input type="date"> uses YYYY-MM-DD.
    return date.fromisoformat(s)


def file_digest_and_bytes(file_bytes: bytes) -> tuple[str, int]:
    h = hashlib.sha256()
    h.update(file_bytes)
    return (h.hexdigest(), len(file_bytes))


def sanitize_upload_filename(filename: str) -> str:
    fn = secure_filename(filename or "")
    return fn or "document.bin"


def import_document_with_revisions(
    s,
    *,
    doc_number: str,
    title: str,
    doc_type: str,
    owner_user,
    category: str | None = None,
    status: str = "Released",
    obsolete_reason: str | None = None,
    revisions: list[dict],
    dry_run: bool = False,
) -> dict:
    """
    Idempotently import a controlled document together with its full revision
    history (Track A). Unlike the interactive UI flow (which builds one Draft
    revision at a time), this loads superseded revisions directly so version
    history is preserved.

    Parameters
    ----------
    doc_number, title, doc_type, category : document identity/metadata
    owner_user : User acting as owner + importer (recorded on revisions/files)
    status : desired final status — "Released" (default), "Obsolete", or "Draft"
    obsolete_reason : required when status == "Obsolete"
    revisions : list of dicts in ascending order, e.g.
        {
            "revision": "A",                 # label (A, B, ... AA, or 1, 2)
            "file_bytes": b"...",            # optional
            "filename": "QM.SLQ001 A.pdf",   # required if file_bytes given
            "content_type": "application/pdf",
            "change_summary": "Initial release",
            "effective_date": date(2020, 1, 1),  # or None
            "released": True,                # historical revs are usually True
            "released_at": datetime(...),    # optional; defaults to now
        }
    dry_run : when True, performs no writes (no storage, no DB) and only
        reports the plan.

    Idempotency
    -----------
    - A document is matched by ``doc_number``; re-running does not duplicate it.
    - A revision is matched by (document, revision label). If it already exists
      with a file, it is skipped. If it exists without a file and a file is
      supplied, the file is attached. New revision labels are created.

    Returns a summary dict describing the actions taken (or that would be taken).
    """
    from flask import current_app

    from app.eqms.audit import record_event
    from app.eqms.modules.document_control.models import (
        Document,
        DocumentFile,
        DocumentRevision,
    )
    from app.eqms.storage import storage_from_config

    doc_number = normalize_doc_number(doc_number)
    if not doc_number or not title or not doc_type:
        raise ValueError("doc_number, title, and doc_type are required.")
    if status not in ("Draft", "Released", "Obsolete"):
        raise ValueError(f"Unsupported status: {status!r}")
    if status == "Obsolete" and not (obsolete_reason or "").strip():
        raise ValueError("Obsolete import requires an obsolete_reason.")
    if not revisions:
        raise ValueError("At least one revision is required.")

    summary: dict = {
        "doc_number": doc_number,
        "document_action": None,  # "create" | "update"
        "revisions_created": [],
        "revisions_skipped": [],
        "files_added": [],
        "final_status": status,
        "dry_run": dry_run,
    }

    existing = (
        s.query(Document).filter(Document.doc_number == doc_number).one_or_none()
    )
    summary["document_action"] = "update" if existing else "create"

    if dry_run:
        existing_labels = set()
        labels_with_files = set()
        if existing:
            for r in existing.revisions:
                existing_labels.add(r.revision)
                if r.files:
                    labels_with_files.add(r.revision)
        for rev in revisions:
            label = str(rev["revision"]).strip().upper()
            has_file = bool(rev.get("file_bytes"))
            if label in existing_labels:
                if label in labels_with_files or not has_file:
                    summary["revisions_skipped"].append(label)
                else:
                    summary["files_added"].append(label)
            else:
                summary["revisions_created"].append(label)
                if has_file:
                    summary["files_added"].append(label)
        return summary

    storage = storage_from_config(current_app.config)

    if existing:
        d = existing
        d.title = title
        d.doc_type = doc_type
        d.category = category
    else:
        d = Document(
            doc_number=doc_number,
            title=title,
            doc_type=doc_type,
            category=category,
            owner_user_id=owner_user.id,
            status="Draft",
        )
        s.add(d)
        s.flush()

    existing_by_label = {r.revision: r for r in d.revisions}
    last_released_rev: DocumentRevision | None = None
    last_rev: DocumentRevision | None = None

    for rev in revisions:
        label = str(rev["revision"]).strip().upper()
        released = bool(rev.get("released", True))
        released_at = rev.get("released_at")
        if released and released_at is None:
            released_at = utcnow()

        r = existing_by_label.get(label)
        if r is None:
            r = DocumentRevision(
                document_id=d.id,
                revision=label,
                change_summary=(rev.get("change_summary") or "").strip(),
                effective_date=rev.get("effective_date"),
                created_by_user_id=owner_user.id,
                released_at=released_at if released else None,
                released_by_user_id=owner_user.id if released else None,
            )
            s.add(r)
            s.flush()
            existing_by_label[label] = r
            summary["revisions_created"].append(label)
            _import_attach_file(
                s, storage, d, r, rev, owner_user, DocumentFile, summary
            )
        else:
            if r.files:
                summary["revisions_skipped"].append(label)
            else:
                _import_attach_file(
                    s, storage, d, r, rev, owner_user, DocumentFile, summary
                )
                if label not in summary["files_added"]:
                    summary["revisions_skipped"].append(label)

        last_rev = r
        if (r.released_at is not None) or released:
            last_released_rev = r

    current = last_released_rev or last_rev
    if current is not None:
        d.current_revision_id = current.id

    if status == "Obsolete":
        d.status = "Obsolete"
    elif last_released_rev is not None:
        d.status = "Released"
    else:
        d.status = "Draft"

    record_event(
        s,
        actor=owner_user,
        action="doc.import",
        entity_type="Document",
        entity_id=str(d.id),
        metadata={
            "doc_number": d.doc_number,
            "created": summary["revisions_created"],
            "skipped": summary["revisions_skipped"],
            "files_added": summary["files_added"],
            "status": d.status,
        },
    )
    if status == "Obsolete":
        record_event(
            s,
            actor=owner_user,
            action="doc.obsolete",
            entity_type="Document",
            entity_id=str(d.id),
            reason=(obsolete_reason or "").strip(),
            metadata={"doc_number": d.doc_number, "via": "import"},
        )

    summary["final_status"] = d.status
    summary["document_id"] = d.id
    return summary


def _import_attach_file(s, storage, d, r, rev, owner_user, DocumentFile, summary):
    """Attach a single file to a revision during import. No-op if none supplied."""
    file_bytes = rev.get("file_bytes")
    if not file_bytes:
        return
    filename = sanitize_upload_filename(rev.get("filename") or "")
    content_type = (rev.get("content_type") or "application/octet-stream").strip()
    sha256, size_bytes = file_digest_and_bytes(file_bytes)
    storage_key = f"documents/{d.doc_number}/rev-{r.revision}/{filename}"
    storage.put_bytes(storage_key, file_bytes, content_type=content_type)
    df = DocumentFile(
        revision_id=r.id,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        sha256=sha256,
        size_bytes=size_bytes,
        uploaded_by_user_id=owner_user.id,
    )
    s.add(df)
    s.flush()
    if r.revision not in summary["files_added"]:
        summary["files_added"].append(r.revision)

