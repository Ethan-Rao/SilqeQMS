from __future__ import annotations

import hashlib
import io
import re
from datetime import date

from werkzeug.utils import secure_filename


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


def to_download_fileobj(file_bytes: bytes) -> io.BytesIO:
    bio = io.BytesIO(file_bytes)
    bio.seek(0)
    return bio

