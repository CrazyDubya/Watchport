from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse
import re
import shlex


def load_config_file() -> None:
    """Read an explicit private environment file; never execute shell syntax."""
    path = Path(os.getenv("WATCHPORT_CONFIG_FILE", "~/.watchport/config.env")).expanduser()
    if not path.exists():
        if "WATCHPORT_CONFIG_FILE" in os.environ:
            raise RuntimeError("WATCHPORT_CONFIG_FILE does not exist")
        return
    info = path.stat()
    if os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise RuntimeError("Watchport config must be owned by this user with mode 0600")
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"WATCHPORT_[A-Z0-9_]+", key):
            raise RuntimeError(f"invalid Watchport config entry on line {number}")
        parts = shlex.split(value, comments=True)
        if len(parts) > 1:
            raise RuntimeError(f"quote spaces in Watchport config line {number}")
        os.environ.setdefault(key, parts[0] if parts else "")


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
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
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
        load_config_file()
        origin = os.getenv("WATCHPORT_ORIGIN", "https://watchport.example-tailnet.ts.net:8443").rstrip("/")
        public_host = _hostname(origin)
        rp_id = os.getenv("WATCHPORT_RP_ID", public_host).strip().lower()
        if rp_id != public_host:
            raise RuntimeError("WATCHPORT_RP_ID must match WATCHPORT_ORIGIN hostname")

        stream_origin = os.getenv("WATCHPORT_STREAM_ORIGIN", f"https://{public_host}:9443").rstrip("/")
        if _hostname(stream_origin) != public_host:
            raise RuntimeError(
                "WATCHPORT_STREAM_ORIGIN must use the same hostname as WATCHPORT_ORIGIN so the scoped player cookie can cross ports"
            )
        if (urlparse(stream_origin).port or 443) == (urlparse(origin).port or 443):
            raise RuntimeError("Watchport and player must use different HTTPS ports to isolate the iframe origin")

        moonlight_origin = os.getenv("WATCHPORT_MOONLIGHT_ORIGIN", "https://127.0.0.1").rstrip("/")
        moonlight_parsed = urlparse(moonlight_origin)
        _hostname(moonlight_origin)
        if not _is_loopback_host(moonlight_parsed.hostname):
            raise RuntimeError("WATCHPORT_MOONLIGHT_ORIGIN must be an https loopback URL")

        secret = os.getenv("WATCHPORT_INDICATOR_SECRET", "")
        if len(secret) < 24:
            raise RuntimeError("WATCHPORT_INDICATOR_SECRET is required and must be at least 24 characters")
        if secret.startswith("replace-with-"):
            raise RuntimeError("replace the example indicator secret with a randomly generated value")
        if not _bool("WATCHPORT_COOKIE_SECURE", True):
            raise RuntimeError("Watchport session cookies must remain Secure")

        host = os.getenv("WATCHPORT_HOST", "127.0.0.1")
        if not _is_loopback_host(host):
            raise RuntimeError(
                "Watchport gateway must bind to loopback; publish it with Tailscale Serve rather than a public/listen-all address"
            )

        app_id = int(os.getenv("WATCHPORT_MOONLIGHT_APP_ID", "-1"))
        moonlight_ttl = int(os.getenv("WATCHPORT_MOONLIGHT_TTL", "3600"))
        if moonlight_ttl not in {3600, 14400, 28800, 86400, 172800}:
            raise RuntimeError(
                "WATCHPORT_MOONLIGHT_TTL must be 3600, 14400, 28800, 86400, or 172800 seconds; unlimited is intentionally forbidden"
            )

        return cls(
            host=host,
            port=_int("WATCHPORT_PORT", 8787),
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
            moonlight_ttl_seconds=moonlight_ttl,
            moonlight_verify_tls=_bool("WATCHPORT_MOONLIGHT_VERIFY_TLS", False),
        )
