from __future__ import annotations

from dataclasses import dataclass
from http.cookiejar import CookieJar
import json
import ssl
from threading import RLock
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


class StreamAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class StreamGrant:
    session_id: str
    slot: int
    viewer_url: str
    cookie_name: str
    cookie_value: str
    cookie_max_age: int
    issued_at: float


class MoonlightTransport:
    """Small localhost-only client for Moonlight-Web's owner/share APIs.

    It intentionally uses only documented/current share primitives. Watchport never
    imports, vendors, or links Moonlight-Web code; this is runtime HTTP integration.
    """

    def __init__(self, origin: str, verify_tls: bool = False, timeout: float = 4.0):
        self.origin = origin.rstrip("/")
        parsed = urlparse(self.origin)
        if parsed.scheme != "https" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise StreamAdapterError("Moonlight-Web control origin must be https loopback")
        self.timeout = timeout
        self.cookies = CookieJar()
        context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies), HTTPSHandler(context=context))

    def _request(self, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
        payload = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        headers = {
            "Accept": "application/json",
            "User-Agent": "Watchport/0.2",
            "Origin": self.origin,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = Request(self.origin + path, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise StreamAdapterError(f"Moonlight-Web {method} {path} returned {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise StreamAdapterError(f"Moonlight-Web is unreachable at {self.origin}: {exc}") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StreamAdapterError(f"Moonlight-Web {path} returned non-JSON data") from exc

    def login_local_owner(self) -> None:
        # This endpoint is localhost-only in Moonlight-Web. Generate a one-use PIN,
        # spend it immediately for an ephemeral owner session, and never persist it.
        generated = self._request("/api/admin/pin/generate", method="POST", body={})
        pin = generated.get("pin")
        if not pin:
            raise StreamAdapterError("Moonlight-Web did not return a local owner PIN")
        result = self._request(
            "/api/auth/validate",
            method="POST",
            body={"pin": pin, "machine_name": "Watchport", "remember": False},
        )
        if result.get("status") != "ok":
            raise StreamAdapterError("Moonlight-Web owner authentication failed")
        if not any(cookie.name == "mw_session" for cookie in self.cookies):
            raise StreamAdapterError("Moonlight-Web did not issue an owner session cookie")

    def deactivate(self, slot: int) -> dict:
        return self._request(f"/api/share/slots/{slot}/deactivate", method="POST", body={})

    def set_viewer_permissions(self, slot: int) -> dict:
        return self._request(
            f"/api/share/slots/{slot}/permissions",
            method="POST",
            body={"gamepad": False, "keyboardMouse": False},
        )

    def activate(self, slot: int, host_uuid: str, app_id: int, ttl_secs: int) -> dict:
        return self._request(
            f"/api/share/slots/{slot}/activate",
            method="POST",
            body={"host_uuid": host_uuid, "app_id": app_id, "ttl_secs": ttl_secs},
        )

    def redeem_player(self, token: str, pin: str) -> str:
        result = self._request(
            "/api/share/player/pin", method="POST", body={"token": token, "pin": pin}
        )
        if result.get("status") != "ok":
            raise StreamAdapterError(f"Moonlight-Web player PIN redemption failed: {result.get('status', 'unknown')}")
        for cookie in self.cookies:
            if cookie.name == "mw_player":
                return cookie.value
        raise StreamAdapterError("Moonlight-Web did not issue the scoped player cookie")

    def status(self) -> dict:
        return self._request("/api/share/status")


class MoonlightWebAdapter:
    """Owns Moonlight-Web player slots exclusively for Watchport sessions.

    Each Watchport stream gets a fresh Moonlight Viewer activation. Closing a
    Watchport stream deactivates the slot, which Moonlight-Web defines as killing
    the live worker first and then invalidating the invitation credentials.
    """

    COOKIE_NAME = "mw_player"

    def __init__(
        self,
        *,
        control_origin: str,
        stream_origin: str,
        slots: tuple[int, ...],
        host_uuid: str,
        app_id: int,
        ttl_seconds: int = 3600,
        verify_tls: bool = False,
        transport: MoonlightTransport | None = None,
    ):
        self.stream_origin = stream_origin.rstrip("/")
        self.slots = slots
        self.host_uuid = host_uuid
        self.app_id = app_id
        self.ttl_seconds = ttl_seconds
        self.transport = transport or MoonlightTransport(control_origin, verify_tls=verify_tls)
        self._grants: dict[str, StreamGrant] = {}
        self._lock = RLock()

    @property
    def configured(self) -> bool:
        return bool(self.host_uuid) and self.app_id >= 0

    def _login(self) -> None:
        self.transport.login_local_owner()

    def _free_slot(self) -> int:
        used = {grant.slot for grant in self._grants.values()}
        for slot in self.slots:
            if slot not in used:
                return slot
        raise StreamAdapterError("all configured Moonlight-Web Viewer slots are in use")

    @staticmethod
    def _token_from_url(url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        marker = "/p/"
        if marker not in path:
            raise StreamAdapterError("Moonlight-Web activation did not return a player URL")
        token = path.rsplit(marker, 1)[1]
        if not token or "/" in token:
            raise StreamAdapterError("Moonlight-Web returned an invalid player token")
        return token

    @staticmethod
    def _assert_viewer(activation: dict) -> None:
        permissions = activation.get("permissions") or {}
        if activation.get("access_level") != "viewer":
            raise StreamAdapterError("Moonlight-Web activation is not backend-enforced Viewer access")
        if permissions.get("gamepad") is not False or permissions.get("keyboardMouse") is not False:
            raise StreamAdapterError("Moonlight-Web activation unexpectedly grants input")

    def open(self, session_id: str, now: float | None = None) -> StreamGrant:
        with self._lock:
            existing = self._grants.get(session_id)
            if existing:
                return existing
            if not self.configured:
                raise StreamAdapterError("Moonlight-Web host/app is not configured")
            slot = self._free_slot()
            self._login()
            # Watchport owns its configured player slots. Removing a stale grant
            # first makes process restarts fail closed instead of reviving it.
            try:
                self.transport.deactivate(slot)
            except StreamAdapterError:
                # Moonlight-Web answers an already-off slot normally in current
                # builds; tolerate older builds that report it as an error.
                pass
            try:
                permission_state = self.transport.set_viewer_permissions(slot)
                permissions = permission_state.get("permissions") or {}
                if permissions.get("gamepad") is not False or permissions.get("keyboardMouse") is not False:
                    raise StreamAdapterError("Moonlight-Web refused Viewer-only permissions")

                activation = self.transport.activate(slot, self.host_uuid, self.app_id, self.ttl_seconds)
                self._assert_viewer(activation)
                raw_url = str(activation.get("url", ""))
                pin = str(activation.get("pin", ""))
                if not pin:
                    raise StreamAdapterError("Moonlight-Web activation did not return a PIN")
                token = self._token_from_url(raw_url)
                player_cookie = self.transport.redeem_player(token, pin)
                issued = time.time() if now is None else now
                grant = StreamGrant(
                    session_id=session_id,
                    slot=slot,
                    viewer_url=f"{self.stream_origin}/p/{token}",
                    cookie_name=self.COOKIE_NAME,
                    cookie_value=player_cookie,
                    cookie_max_age=min(self.ttl_seconds, 3600),
                    issued_at=issued,
                )
                self._grants[session_id] = grant
                return grant
            except Exception:
                try:
                    self.transport.deactivate(slot)
                except Exception:
                    pass
                raise

    def close(self, session_id: str) -> bool:
        with self._lock:
            grant = self._grants.pop(session_id, None)
            if not grant:
                return False
            self._login()
            self.transport.deactivate(grant.slot)
            return True

    def cleanup_stale_slots(self) -> None:
        with self._lock:
            self._login()
            for slot in self.slots:
                try:
                    self.transport.deactivate(slot)
                except StreamAdapterError:
                    continue
            self._grants.clear()

    def revoke_all(self) -> None:
        with self._lock:
            session_ids = list(self._grants)
        for session_id in session_ids:
            try:
                self.close(session_id)
            except StreamAdapterError:
                # Keep attempting every known grant; callers treat any failed
                # transport as a degraded/fail-closed state and surface it.
                continue

    def grant_for(self, session_id: str) -> StreamGrant | None:
        with self._lock:
            return self._grants.get(session_id)

    def active_count(self) -> int:
        with self._lock:
            return len(self._grants)
