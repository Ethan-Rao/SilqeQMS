import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    env: str
    database_url: str

    storage_backend: str
    s3_endpoint: str
    s3_region: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    storage_local_root: str


def _getenv(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def load_settings() -> Settings:
    return Settings(
        secret_key=_getenv("SECRET_KEY", "change-me"),
        env=_getenv("ENV", "development"),
        database_url=_getenv("DATABASE_URL", "sqlite:///eqms.db"),
        storage_backend=_getenv("STORAGE_BACKEND", "local"),
        s3_endpoint=_getenv("S3_ENDPOINT", ""),
        s3_region=_getenv("S3_REGION", "nyc3"),
        s3_bucket=_getenv("S3_BUCKET", ""),
        s3_access_key_id=_getenv("S3_ACCESS_KEY_ID", ""),
        s3_secret_access_key=_getenv("S3_SECRET_ACCESS_KEY", ""),
        storage_local_root=_getenv("STORAGE_LOCAL_ROOT", ""),
    )


def _truthy_env(name: str) -> bool:
    v = (_getenv(name) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _safe_int_mb(raw: str, *, default: int) -> int:
    try:
        n = int((raw or str(default)).strip())
    except ValueError:
        return default
    return max(1, n)


def load_config() -> dict:
    s = load_settings()
    is_production = s.env in ("prod", "production")
    return {
        "SECRET_KEY": s.secret_key,
        "ENV": s.env,
        "DATABASE_URL": s.database_url,
        "STORAGE_BACKEND": s.storage_backend,
        "S3_ENDPOINT": s.s3_endpoint,
        "S3_REGION": s.s3_region,
        "S3_BUCKET": s.s3_bucket,
        "S3_ACCESS_KEY_ID": s.s3_access_key_id,
        "S3_SECRET_ACCESS_KEY": s.s3_secret_access_key,
        "STORAGE_LOCAL_ROOT": s.storage_local_root,
        # security defaults
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": is_production,  # Require HTTPS in production
        # Temporary auditor files portal (see docs/DEV_AGENT_PROMPT_AUDITOR_FILES_PORTAL.md)
        "AUDITOR_PORTAL_ENABLED": "1" if _truthy_env("AUDITOR_PORTAL_ENABLED") else "0",
        "AUDITOR_FILES_ROOT": _getenv("AUDITOR_FILES_ROOT"),
        "AUDITOR_MAX_FILE_MB": _safe_int_mb(_getenv("AUDITOR_MAX_FILE_MB"), default=50),
        "AUDITOR_PDF_BACKEND": (_getenv("AUDITOR_PDF_BACKEND") or "auto").strip().lower(),
    }

