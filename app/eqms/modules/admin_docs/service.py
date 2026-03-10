from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from werkzeug.utils import secure_filename

from app.eqms.audit import record_event
from app.eqms.storage import storage_from_config
from app.eqms.utils import utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User
    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder


def _digest(file_bytes: bytes) -> tuple[str, int]:
    h = hashlib.sha256()
    h.update(file_bytes)
    return h.hexdigest(), len(file_bytes)


def build_admin_doc_storage_key(library_key: str, folder_path: str, filename: str) -> str:
    safe_library = library_key.replace("/", "_").replace("\\", "_")
    safe_folder = folder_path.strip("/").replace("\\", "/")
    safe_filename = secure_filename(filename) or "document.bin"
    if safe_folder:
        return f"admin_docs/{safe_library}/{safe_folder}/{safe_filename}"
    return f"admin_docs/{safe_library}/{safe_filename}"


def create_folder(
    s: "Session",
    library_key: str,
    name: str,
    user: "User",
    parent: "AdminDocFolder | None" = None,
    description: str | None = None,
) -> "AdminDocFolder":
    from app.eqms.modules.admin_docs.models import AdminDocFolder

    folder = AdminDocFolder(
        library_key=library_key,
        parent_id=parent.id if parent else None,
        name=name.strip(),
        description=(description or "").strip() or None,
        created_at=utcnow(),
        created_by_user_id=user.id,
    )
    s.add(folder)
    s.flush()

    record_event(
        s,
        actor=user,
        action="admin_docs.folder_create",
        entity_type="AdminDocFolder",
        entity_id=str(folder.id),
        metadata={"library_key": library_key, "name": folder.name},
    )
    return folder


def upload_document(
    s: "Session",
    library_key: str,
    folder: "AdminDocFolder | None",
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user: "User",
    description: str | None = None,
) -> "AdminDocFile":
    from app.eqms.modules.admin_docs.models import AdminDocFile
    from app.eqms.modules.admin_docs.utils import build_folder_path
    from flask import current_app

    sha256, size_bytes = _digest(file_bytes)
    folder_path = build_folder_path(s, folder) if folder else ""
    storage_key = build_admin_doc_storage_key(library_key, folder_path, filename)

    storage = storage_from_config(current_app.config)
    storage.put_bytes(storage_key, file_bytes, content_type=content_type)

    doc = AdminDocFile(
        library_key=library_key,
        folder_id=folder.id if folder else None,
        filename=secure_filename(filename) or "document.bin",
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
        description=(description or "").strip() or None,
        uploaded_at=utcnow(),
        uploaded_by_user_id=user.id,
    )
    s.add(doc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="admin_docs.document_upload",
        entity_type="AdminDocFile",
        entity_id=str(doc.id),
        metadata={"library_key": library_key, "filename": doc.filename, "sha256": sha256},
    )
    return doc
