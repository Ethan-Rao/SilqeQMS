from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class StorageError(RuntimeError):
    pass


class Storage:
    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        raise NotImplementedError

    def open(self, key: str) -> BinaryIO:
        raise NotImplementedError

    def get_bytes(self, key: str) -> bytes:
        fobj = self.open(key)
        try:
            return fobj.read()
        finally:
            try:
                fobj.close()
            except Exception:
                pass

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class LocalStorage(Storage):
    root: Path

    def _path(self, key: str) -> Path:
        safe_key = key.lstrip("/").replace("\\", "/")
        # Reject keys containing path traversal attempts
        if ".." in safe_key:
            raise StorageError(f"Invalid storage key (path traversal detected): {key}")
        return self.root / safe_key

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def open(self, key: str) -> BinaryIO:
        p = self._path(key)
        return p.open("rb")

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> bool:
        p = self._path(key)
        if p.exists():
            p.unlink()
            return True
        return False

    def list_keys(self, prefix: str) -> list[str]:
        safe = prefix.lstrip("/").replace("\\", "/")
        if ".." in safe:
            raise StorageError(f"Invalid storage prefix: {prefix}")
        root = self.root / safe
        if not root.exists():
            # prefix may be a directory path like temp_po_pdf/
            base = self.root / safe.rstrip("/")
            if not base.exists():
                return []
            root = base
        out: list[str] = []
        base_dir = self.root / safe.rstrip("/")
        if base_dir.is_file():
            return [safe.rstrip("/")]
        if not base_dir.is_dir():
            return []
        for p in base_dir.rglob("*"):
            if p.is_file():
                out.append(p.relative_to(self.root).as_posix())
        return out

    def key_mtime(self, key: str) -> float | None:
        p = self._path(key)
        if not p.exists():
            return None
        return p.stat().st_mtime


@dataclass(frozen=True)
class S3Storage(Storage):
    endpoint: str
    region: str
    bucket: str
    access_key_id: str
    secret_access_key: str

    def _client(self):
        # Cache the boto3 client on the instance to avoid repeated creation (F-010)
        cached = getattr(self, "_cached_client", None)
        if cached is not None:
            return cached
        try:
            import boto3  # type: ignore
        except Exception as e:  # pragma: no cover
            raise StorageError("boto3 required for S3 storage. Install boto3.") from e
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{self.endpoint}" if self.endpoint else None,
            region_name=self.region or None,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        # frozen dataclass — use object.__setattr__ to cache
        object.__setattr__(self, "_cached_client", client)
        return client

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        extra: dict[str, object] = {}
        if content_type:
            extra["ContentType"] = content_type
        self._client().put_object(Bucket=self.bucket, Key=key, Body=data, **extra)

    def open(self, key: str) -> BinaryIO:
        obj = self._client().get_object(Bucket=self.bucket, Key=key)
        return obj["Body"]  # type: ignore[return-value]

    def exists(self, key: str) -> bool:
        try:
            self._client().head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        try:
            self._client().delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def list_keys(self, prefix: str) -> list[str]:
        out: list[str] = []
        token = None
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = self._client().list_objects_v2(**kwargs)
            for obj in resp.get("Contents") or []:
                k = obj.get("Key")
                if k:
                    out.append(k)
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
        return out

    def key_mtime(self, key: str) -> float | None:
        try:
            resp = self._client().head_object(Bucket=self.bucket, Key=key)
            lm = resp.get("LastModified")
            if lm is None:
                return None
            return float(lm.timestamp())
        except Exception:
            return None

def storage_from_config(config: dict) -> Storage:
    backend = (config.get("STORAGE_BACKEND") or "local").strip().lower()
    if backend == "s3":
        return S3Storage(
            endpoint=(config.get("S3_ENDPOINT") or "").strip(),
            region=(config.get("S3_REGION") or "nyc3").strip(),
            bucket=(config.get("S3_BUCKET") or "").strip(),
            access_key_id=(config.get("S3_ACCESS_KEY_ID") or "").strip(),
            secret_access_key=(config.get("S3_SECRET_ACCESS_KEY") or "").strip(),
        )
    # default local
    root_override = (config.get("STORAGE_LOCAL_ROOT") or "").strip()
    if root_override:
        root = Path(root_override)
    else:
        root = Path(__file__).resolve().parents[2] / "storage"
    return LocalStorage(root=root)

