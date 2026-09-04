from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, *, minimum: int = 1) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}")
    return value


def _slots(value: str) -> tuple[int, ...]:
    result = tuple(dict.fromkeys(int(part.strip()) for part in value.split(",") if part.strip()))
    if not result or any(slot not in {2, 3, 4} for slot in result):
        raise RuntimeError("WATCHPORT_MOONLIGHT_SLOTS must contain only player slots 2, 3, and/or 4")
    return result


def _hostname(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"expected an https URL, got {url!r}")
    return parsed.hostname.lower()


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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
    viewer_heartbeat_timeout_seconds: int
    indicator_timeout_seconds: int
    indicator_secret: str
    moonlight_origin: str
    stream_origin: str
    moonlight_slots: tuple[int, ...]
    moonlight_host_uuid: str
    moonlight_app_id: int
    moonlight_ttl_seconds: int
    moonlight_verify_tls: bool

    @property
    def stream_configured(self) -> bool:
        return bool(self.moonlight_host_uuid) and self.moonlight_app_id >= 0

    @property
    def public_hostname(self) -> str:
        return _hostname(self.origin)

    @classmethod
    def from_env(cls) -> "Settings":
        origin = os.getenv("WATCHPORT_ORIGIN", "https://watchport.example-tailnet.ts.net:8443").rstrip("/")
        public_host = _hostname(origin)
        rp_id = os.getenv("WATCHPORT_RP_ID", public_host).strip().lower()
        if rp_id != public_host:
            raise RuntimeError("WATCHPORT_RP_ID must match WATCHPORT_ORIGIN hostname")

        stream_origin = os.getenv("WATCHPORT_STREAM_ORIGIN", f"https://{public_host}").rstrip("/")
        if _hostname(stream_origin) != public_host:
            raise RuntimeError(
                "WATCHPORT_STREAM_ORIGIN must use the same hostname as WATCHPORT_ORIGIN so the scoped player cookie can cross ports"
            )

        moonlight_origin = os.getenv("WATCHPORT_MOONLIGHT_ORIGIN", "https://127.0.0.1").rstrip("/")
        moonlight_parsed = urlparse(moonlight_origin)
        if moonlight_parsed.scheme != "https" or not _is_loopback_host(moonlight_parsed.hostname):
            raise RuntimeError("WATCHPORT_MOONLIGHT_ORIGIN must be an https loopback URL")

        secret = os.getenv("WATCHPORT_INDICATOR_SECRET", "")
        if len(secret) < 24:
            raise RuntimeError("WATCHPORT_INDICATOR_SECRET is required and must be at least 24 characters")

        host = os.getenv("WATCHPORT_HOST", "127.0.0.1")
        if not _is_loopback_host(host):
            raise RuntimeError(
                "Watchport gateway must bind to loopback; publish it with Tailscale Serve rather than a public/listen-all address"
            )

        app_id_raw = os.getenv("WATCHPORT_MOONLIGHT_APP_ID", "-1")
        app_id = int(app_id_raw)

        return cls(
            host=host,
            port=_int("WATCHPORT_PORT", 8443),
            origin=origin,
            rp_id=rp_id,
            data_dir=Path(os.getenv("WATCHPORT_DATA_DIR", "~/.watchport")).expanduser(),
            cookie_secure=_bool("WATCHPORT_COOKIE_SECURE", True),
            session_ttl_seconds=_int("WATCHPORT_SESSION_TTL", 900, minimum=60),
            admission_ttl_seconds=_int("WATCHPORT_ADMISSION_TTL", 60, minimum=10),
            viewer_heartbeat_timeout_seconds=_int("WATCHPORT_VIEWER_HEARTBEAT_TIMEOUT", 12, minimum=6),
            indicator_timeout_seconds=_int("WATCHPORT_INDICATOR_TIMEOUT", 6, minimum=3),
            indicator_secret=secret,
            moonlight_origin=moonlight_origin,
            stream_origin=stream_origin,
            moonlight_slots=_slots(os.getenv("WATCHPORT_MOONLIGHT_SLOTS", "2,3,4")),
            moonlight_host_uuid=os.getenv("WATCHPORT_MOONLIGHT_HOST_UUID", "").strip(),
            moonlight_app_id=app_id,
            moonlight_ttl_seconds=_int("WATCHPORT_MOONLIGHT_TTL", 3600, minimum=3600),
            moonlight_verify_tls=_bool("WATCHPORT_MOONLIGHT_VERIFY_TLS", False),
        )
