from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    origin: str
    rp_id: str
    data_dir: Path
    cookie_secure: bool
    session_ttl_seconds: int
    admission_ttl_seconds: int
    indicator_timeout_seconds: int
    indicator_secret: str
    viewer_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        origin = os.getenv("WATCHPORT_ORIGIN", "https://watchport.local:8443").rstrip("/")
        rp_id = os.getenv("WATCHPORT_RP_ID", origin.split("://", 1)[-1].split(":", 1)[0])
        secret = os.getenv("WATCHPORT_INDICATOR_SECRET", "")
        if not secret:
            raise RuntimeError("WATCHPORT_INDICATOR_SECRET is required")
        return cls(
            host=os.getenv("WATCHPORT_HOST", "127.0.0.1"),
            port=int(os.getenv("WATCHPORT_PORT", "8443")),
            origin=origin,
            rp_id=rp_id,
            data_dir=Path(os.getenv("WATCHPORT_DATA_DIR", "~/.watchport")).expanduser(),
            cookie_secure=_bool("WATCHPORT_COOKIE_SECURE", True),
            session_ttl_seconds=int(os.getenv("WATCHPORT_SESSION_TTL", "900")),
            admission_ttl_seconds=int(os.getenv("WATCHPORT_ADMISSION_TTL", "300")),
            indicator_timeout_seconds=int(os.getenv("WATCHPORT_INDICATOR_TIMEOUT", "6")),
            indicator_secret=secret,
            viewer_url=os.getenv("WATCHPORT_VIEWER_URL", ""),
        )
