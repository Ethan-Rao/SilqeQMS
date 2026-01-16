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

    def exists(self, key: str) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class LocalStorage(Storage):
    root: Path

    def _path(self, key: str) -> Path:
        safe_key = key.lstrip("/").replace("\\", "/")
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


@dataclass(frozen=True)
class S3Storage(Storage):
    endpoint: str
    region: str
    bucket: str
    access_key_id: str
    secret_access_key: str

    def _client(self):
        try:
            import boto3  # type: ignore
        except Exception as e:  # pragma: no cover
            raise StorageError("boto3 required for S3 storage. Install boto3.") from e
        return boto3.client(
            "s3",
            endpoint_url=f"https://{self.endpoint}" if self.endpoint else None,
            region_name=self.region or None,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )

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
    root = Path(os.getcwd()) / "storage"
    return LocalStorage(root=root)

