from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.modules.admin_docs.models import AdminDocFolder


def build_folder_path(s: "Session", folder: "AdminDocFolder | None") -> str:
    if not folder:
        return ""
    parts: list[str] = []
    current = folder
    while current:
        parts.append(current.name.replace("/", "_").replace("\\", "_"))
        if not current.parent_id:
            break
        current = s.get(type(folder), current.parent_id)
    return "/".join(reversed(parts))
