from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

from flask import abort, current_app

logger = logging.getLogger(__name__)

_ROOT: Path | None = None
_ROOT_WARNED = False


def get_auditor_root() -> Path | None:
    """Resolve AUDITOR_FILES_ROOT once; return None if unusable."""
    global _ROOT, _ROOT_WARNED
    if _ROOT is not None:
        return _ROOT if _ROOT.exists() and _ROOT.is_dir() else None

    root_raw = (current_app.config.get("AUDITOR_FILES_ROOT") or "").strip()
    if not root_raw:
        base = Path(current_app.root_path).resolve().parent.parent
        root = base / "Auditor Files"
    else:
        root = Path(root_raw).expanduser()
    try:
        _ROOT = root.resolve(strict=False)
    except Exception:
        _ROOT = root
    if not _ROOT.exists() or not _ROOT.is_dir():
        if not _ROOT_WARNED:
            _ROOT_WARNED = True
            logger.warning("AUDITOR_FILES_ROOT is missing or not a directory: %s", _ROOT)
        return None
    return _ROOT


def _safe_resolve(rel: str) -> Path:
    root = get_auditor_root()
    if root is None:
        abort(404)
    rel = (rel or "").strip().lstrip("/\\")
    candidate = (root / rel).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        abort(404)
    return candidate


class DirEntry(NamedTuple):
    name: str
    rel_path: str
    is_dir: bool
    size: int | None


def list_immediate(rel: str) -> tuple[list[DirEntry], list[DirEntry]]:
    """Return (subdirs, files) under rel (non-recursive)."""
    base = _safe_resolve(rel)
    if not base.is_dir():
        abort(404)
    subdirs: list[DirEntry] = []
    files: list[DirEntry] = []
    root = get_auditor_root()
    assert root is not None
    try:
        for child in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            name = child.name
            if name.startswith(".") or name.startswith("~$"):
                continue
            try:
                resolved = child.resolve(strict=False)
                resolved.relative_to(root)
            except ValueError:
                continue
            if child.is_symlink():
                try:
                    resolved.relative_to(root)
                except ValueError:
                    continue
            rel_path = str(child.relative_to(root)).replace("\\", "/")
            if child.is_dir():
                subdirs.append(DirEntry(name=name, rel_path=rel_path, is_dir=True, size=None))
            elif child.is_file():
                try:
                    sz = child.stat().st_size
                except OSError:
                    sz = None
                files.append(DirEntry(name=name, rel_path=rel_path, is_dir=False, size=sz))
    except OSError:
        abort(404)
    return subdirs, files


def count_files_non_recursive(folder: Path) -> int:
    root = get_auditor_root()
    if root is None or not folder.is_dir():
        return 0
    n = 0
    try:
        for child in folder.iterdir():
            if child.name.startswith(".") or child.name.startswith("~$"):
                continue
            if child.is_file():
                n += 1
    except OSError:
        return 0
    return n


def _count_files_recursive(folder: Path) -> int:
    """Count all non-hidden files under folder (recursive). Bounded walk:
    skips hidden and Office-temp entries; swallows OSError to stay robust
    on unreadable subtrees."""
    total = 0
    try:
        for child in folder.iterdir():
            name = child.name
            if name.startswith(".") or name.startswith("~$"):
                continue
            try:
                if child.is_file():
                    total += 1
                elif child.is_dir():
                    total += _count_files_recursive(child)
            except OSError:
                continue
    except OSError:
        return total
    return total


class SubfolderInfo(NamedTuple):
    name: str
    rel_path: str
    total_files: int


class FileInfo(NamedTuple):
    name: str
    rel_path: str


class FolderTile(NamedTuple):
    name: str
    rel_path: str
    total_files: int
    subfolders: list[SubfolderInfo]
    files: list[FileInfo]


def _list_immediate_children(folder: Path, root: Path) -> tuple[list[SubfolderInfo], list[FileInfo]]:
    """Enumerate immediate subfolders + files under folder (non-recursive).

    Subfolders include their own recursive file counts so the dashboard
    dropdown can show "<name>  <count>". Files are name + rel_path only;
    file size is already displayed inside the browse view. Hidden entries
    and Office temp files (``~$*``) are skipped at both levels.
    """
    subs: list[SubfolderInfo] = []
    files: list[FileInfo] = []
    try:
        for child in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            name = child.name
            if name.startswith(".") or name.startswith("~$"):
                continue
            try:
                rel = str(child.relative_to(root)).replace("\\", "/")
            except ValueError:
                continue
            try:
                if child.is_dir():
                    subs.append(
                        SubfolderInfo(
                            name=name,
                            rel_path=rel,
                            total_files=_count_files_recursive(child),
                        )
                    )
                elif child.is_file():
                    files.append(FileInfo(name=name, rel_path=rel))
            except OSError:
                continue
    except OSError:
        return subs, files
    return subs, files


def top_level_folders() -> list[FolderTile]:
    """Dashboard tiles: each top-level subfolder of ROOT, with a recursive
    file count plus its immediate subfolders (each with its own recursive
    count) AND immediate files, so the UI can offer direct navigation
    into nested sections or straight to individual files."""
    root = get_auditor_root()
    if root is None:
        return []
    out: list[FolderTile] = []
    try:
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            subs, files = _list_immediate_children(child, root)
            out.append(
                FolderTile(
                    name=child.name,
                    rel_path=child.name,
                    total_files=_count_files_recursive(child),
                    subfolders=subs,
                    files=files,
                )
            )
    except OSError:
        return []
    return out


def max_file_bytes() -> int:
    mb = int(current_app.config.get("AUDITOR_MAX_FILE_MB") or 50)
    return max(1, mb) * 1024 * 1024


def read_file_bytes(rel_path: str) -> tuple[bytes, int]:
    p = _safe_resolve(rel_path)
    if not p.is_file():
        abort(404)
    max_b = max_file_bytes()
    try:
        st = p.stat()
    except OSError:
        abort(404)
    if st.st_size > max_b:
        abort(413)
    try:
        data = p.read_bytes()
    except OSError:
        abort(404)
    return data, st.st_size


def cache_key_parts(rel_path: str, size: int, mtime_ns: int) -> str:
    import hashlib

    h = hashlib.sha256(f"{rel_path}|{size}|{mtime_ns}".encode()).hexdigest()
    return h


def reset_auditor_root_cache_for_tests() -> None:
    """Clear cached root (tests / multi-app instances)."""
    global _ROOT, _ROOT_WARNED
    _ROOT = None
    _ROOT_WARNED = False
