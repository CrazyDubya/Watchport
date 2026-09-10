from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import secrets
from threading import RLock
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .audit import AuditLog
from .bootstrap import BootstrapToken
from .config import Settings
from .indicator_state import IndicatorState
from .sessions import SessionManager, State
from .store import CredentialStore
from .stream_adapter import MoonlightWebAdapter, StreamAdapterError
from .webauthn_service import WebAuthnService

COOKIE = "watchport_session"
PLAYER_COOKIE = "mw_player"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = CredentialStore(settings.data_dir / "watchport.sqlite3")
    auth = WebAuthnService(settings.rp_id, settings.origin, store)
    sessions = SessionManager(settings.session_ttl_seconds, settings.admission_ttl_seconds)
    indicator = IndicatorState(settings.indicator_secret, settings.indicator_timeout_seconds)
    bootstrap = BootstrapToken(settings.data_dir)
    audit = AuditLog(settings.data_dir / "audit.jsonl")
    if store.count() == 0:
        bootstrap.ensure()

    adapter = MoonlightWebAdapter(
        control_origin=settings.moonlight_origin,
        stream_origin=settings.stream_origin,
        slots=settings.moonlight_slots,
        host_uuid=settings.moonlight_host_uuid,
        app_id=settings.moonlight_app_id,
        ttl_seconds=settings.moonlight_ttl_seconds,
        verify_tls=settings.moonlight_verify_tls,
        lock_path=settings.data_dir / "moonlight-control.lock",
    )

    lifecycle = RLock()
    challenges: dict[str, tuple[bytes, float, str]] = {}
    challenge_lock = RLock()
    runtime = {"adapterHealthy": True, "lastAdapterError": ""}

    def adapter_error(exc: Exception) -> None:
        runtime["adapterHealthy"] = False
        runtime["lastAdapterError"] = str(exc)[:240]

    def adapter_ok() -> None:
        runtime["adapterHealthy"] = True
        runtime["lastAdapterError"] = ""

    def revoke_stream(session, *, reason: str, close_session: bool) -> bool:
        with lifecycle:
            try:
                adapter.close(session.token)
                if adapter.uncertain:
                    raise StreamAdapterError("upstream revocation remains uncertain")
                adapter_ok()
            except StreamAdapterError as exc:
                adapter_error(exc)
                audit.event("stream_revoke_failed", reason=reason, error=type(exc).__name__)
                return False
            indicator.viewer_stop(session.token)
            if close_session:
                sessions.close(session)
            else:
                sessions.stop_stream(session)
            audit.event("stream_revoked", reason=reason)
            return True

    def recover_slots() -> None:
        with lifecycle:
            try:
                adapter.cleanup_stale_slots()
            except StreamAdapterError as exc:
                adapter_error(exc)
                return
            for session in sessions.streaming():
                sessions.close(session)
            indicator.clear()
            adapter_ok()
            audit.event("stream_slots_recovered")

    async def watchdog() -> None:
        last_recovery = 0.0
        while True:
            if not runtime["adapterHealthy"] and time.monotonic() - last_recovery > 5:
                last_recovery = time.monotonic()
                await asyncio.to_thread(recover_slots)
            now = time.time()
            indicator_healthy = indicator.healthy(now)
            for session in sessions.streaming():
                if now >= session.expires_at:
                    await asyncio.to_thread(revoke_stream, session, reason="session_expired", close_session=True)
                    continue
                if not indicator_healthy:
                    await asyncio.to_thread(revoke_stream, session, reason="indicator_unhealthy", close_session=True)
                    continue
                if now - session.viewer_last_seen_at > settings.viewer_heartbeat_timeout_seconds:
                    await asyncio.to_thread(revoke_stream, session, reason="viewer_heartbeat_lost", close_session=False)
            await asyncio.sleep(1)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Watchport owns only the configured Moonlight player slots. A restart
        # invalidates anything left in them before accepting new viewing.
        if adapter.configured:
            try:
                await asyncio.to_thread(adapter.cleanup_stale_slots)
                adapter_ok()
                audit.event("stream_slots_cleaned_on_start")
            except StreamAdapterError as exc:
                adapter_error(exc)
                audit.event("stream_adapter_startup_degraded", error=type(exc).__name__)
        task = asyncio.create_task(watchdog(), name="watchport-watchdog")
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await asyncio.to_thread(adapter.revoke_all)
            indicator.clear()

    app = FastAPI(
        title="Watchport", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[settings.public_hostname, "localhost", "127.0.0.1", "[::1]"],
    )
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), clipboard-read=(), clipboard-write=(), usb=(), serial=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            f"connect-src 'self'; frame-src {settings.stream_origin}; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/")
    def index():
        return FileResponse(static_dir / "index.html")

    def session_for(request: Request):
        return sessions.get(request.cookies.get(COOKIE))

    def require_session(request: Request):
        session = session_for(request)
        if not session:
            raise HTTPException(401, "passkey authentication required")
        return session

    def require_csrf(request: Request, session) -> None:
        supplied = request.headers.get("x-watchport-csrf", "")
        if not supplied or not secrets.compare_digest(supplied, session.csrf):
            raise HTTPException(403, "CSRF check failed")

    def registration_authorized(request: Request) -> tuple[str, object | None]:
        if store.count() == 0:
            supplied = request.headers.get("x-watchport-bootstrap", "")
            if not bootstrap.verify(supplied):
                raise HTTPException(403, "valid one-time bootstrap token required")
            return "bootstrap", None
        session = require_session(request)
        require_csrf(request, session)
        return "authenticated", session

    def new_challenge(kind: str, authority: str) -> tuple[str, bytes]:
        key = secrets.token_urlsafe(24)
        challenge = secrets.token_bytes(32)
        now = time.time()
        with challenge_lock:
            for old_key, (_, expires, _) in list(challenges.items()):
                if now > expires:
                    challenges.pop(old_key, None)
            challenges[f"{kind}:{key}"] = (challenge, now + 120, authority)
        return key, challenge

    def take_challenge(kind: str, key: str, authority: str | None = None) -> bytes:
        with challenge_lock:
            item = challenges.pop(f"{kind}:{key}", None)
        if not item or time.time() > item[1]:
            raise HTTPException(400, "challenge expired")
        if authority is not None and item[2] != authority:
            raise HTTPException(403, "challenge authority changed")
        return item[0]

    @app.get("/api/status")
    def status(request: Request):
        session = session_for(request)
        return {
            "enrolled": store.count() > 0,
            "authenticated": bool(session),
            "csrf": session.csrf if session else None,
            "state": session.state if session else None,
            "indicatorHealthy": indicator.healthy(),
            "viewers": indicator.viewer_count(),
            "streamConfigured": settings.stream_configured,
            "adapterHealthy": runtime["adapterHealthy"],
        }

    @app.post("/api/passkeys/register/options")
    def register_options(request: Request):
        authority, _ = registration_authorized(request)
        key, challenge = new_challenge("register", authority)
        return JSONResponse(
            {"challengeKey": key, "options": json.loads(auth.registration_options(challenge))}
        )

    @app.post("/api/passkeys/register/verify")
    async def register_verify(request: Request):
        authority, _ = registration_authorized(request)
        body = await request.json()
        try:
            auth.verify_registration(
                body["credential"], take_challenge("register", body["challengeKey"], authority)
            )
        except HTTPException:
            raise
        except Exception as exc:
            audit.event("passkey_registration_failed", error=type(exc).__name__)
            raise HTTPException(400, "passkey registration verification failed") from exc
        if authority == "bootstrap":
            bootstrap.consume()
        audit.event("passkey_registered", authority=authority)
        return {"ok": True}

    @app.post("/api/passkeys/auth/options")
    def authentication_options():
        if store.count() == 0:
            raise HTTPException(409, "no passkey enrolled")
        key, challenge = new_challenge("auth", "passkey")
        return JSONResponse(
            {"challengeKey": key, "options": json.loads(auth.authentication_options(challenge))}
        )

    @app.post("/api/passkeys/auth/verify")
    async def authentication_verify(request: Request, response: Response):
        body = await request.json()
        try:
            auth.verify_authentication(
                body["credential"], take_challenge("auth", body["challengeKey"], "passkey")
            )
        except HTTPException:
            raise
        except Exception as exc:
            audit.event("passkey_auth_failed", error=type(exc).__name__)
            raise HTTPException(401, "passkey authentication failed") from exc
        session = sessions.create()
        response.set_cookie(
            COOKIE,
            session.token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=settings.session_ttl_seconds,
            path="/",
        )
        audit.event("passkey_auth_success")
        return {"ok": True, "csrf": session.csrf}

    @app.post("/api/logout")
    def logout(request: Request, response: Response):
        with lifecycle:
            session = require_session(request)
            require_csrf(request, session)
            if session.state == State.STREAMING and not revoke_stream(
                session, reason="logout", close_session=True
            ):
                raise HTTPException(503, "could not prove the external stream was revoked")
            else:
                sessions.close(session)
            response.delete_cookie(COOKIE, path="/")
            response.delete_cookie(PLAYER_COOKIE, path="/", secure=True, samesite="strict")
            audit.event("logout")
            return {"ok": True}


    @app.post("/api/view/start")
    def view_start(request: Request, response: Response):
        with lifecycle:
            session = require_session(request)
            require_csrf(request, session)
            if not settings.stream_configured:
                raise HTTPException(503, "Moonlight-Web host/app is not configured")
            if not runtime["adapterHealthy"] or adapter.uncertain:
                raise HTTPException(503, "stream cleanup is unresolved; admission blocked")
            if not indicator.healthy():
                raise HTTPException(503, "host indicator is not healthy")
            started = time.monotonic()
            try:
                if session.state != State.STREAMING:
                    sessions.admit(session, True)
                    # Reserve visible warning state BEFORE minting any authority.
                    indicator.viewer_start(session.token)
                deadline = time.monotonic() + settings.indicator_timeout_seconds
                while not indicator.confirmed(session.token):
                    if time.monotonic() >= deadline or not indicator.healthy():
                        raise PermissionError("host warning was not acknowledged")
                    time.sleep(0.05)
                grant = adapter.open(session.token)
                if not indicator.confirmed(session.token):
                    raise PermissionError("host warning acknowledgement expired")
                if session.state != State.STREAMING:
                    sessions.start_stream(session)
                elif sessions.get(session.token) is None:
                    raise PermissionError("session expired during admission")
                adapter_ok()
                admission_ms = round((time.monotonic() - started) * 1000)
                audit.event("stream_started", slot=grant.slot, admission_ms=admission_ms)
            except (PermissionError, StreamAdapterError) as exc:
                # Includes expiry AFTER upstream minting; never abandon authority
                # simply because the local state transition failed.
                revoked = revoke_stream(session, reason="admission_failed", close_session=False)
                if adapter.uncertain or not revoked:
                    adapter_error(exc)
                elif session.state != State.STREAMING:
                    indicator.viewer_stop(session.token)
                audit.event("stream_start_failed", error=type(exc).__name__)
                raise HTTPException(503, "view could not start safely; check host status") from exc
            response.set_cookie(
                grant.cookie_name, grant.cookie_value, httponly=True,
                secure=True, samesite="strict", max_age=min(grant.cookie_max_age, max(1, int(session.expires_at - time.time()))), path="/",
            )
            return {"viewerUrl": grant.viewer_url, "startedAt": session.stream_started_at, "admissionMs": admission_ms}

    @app.post("/api/view/heartbeat")
    def view_heartbeat(request: Request):
        session = require_session(request)
        require_csrf(request, session)
        try:
            sessions.touch_viewer(session)
        except PermissionError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"ok": True}

    @app.post("/api/view/stop")
    def view_stop(request: Request, response: Response):
        with lifecycle:
            session = require_session(request)
            require_csrf(request, session)
            if session.state == State.STREAMING and not revoke_stream(
                session, reason="user_stop", close_session=False
            ):
                raise HTTPException(503, "could not prove the external stream was revoked")
            response.delete_cookie(PLAYER_COOKIE, path="/", secure=True, samesite="strict")
            return {"ok": True}


    @app.post("/internal/indicator/heartbeat")
    async def indicator_heartbeat(request: Request):
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            raise HTTPException(403, "indicator endpoint is localhost-only")
        if not indicator.authenticate(request.headers.get("x-watchport-indicator", "")):
            raise HTTPException(401, "bad indicator secret")
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, "render acknowledgement required")
        token = body.get("renderedToken") if isinstance(body, dict) else None
        if token is not None and not isinstance(token, str):
            raise HTTPException(400, "invalid render acknowledgement")
        indicator.heartbeat(rendered_token=token)
        return indicator.snapshot()

    @app.get("/internal/indicator/state")
    def indicator_state(request: Request):
        if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
            raise HTTPException(403)
        if not indicator.authenticate(request.headers.get("x-watchport-indicator", "")):
            raise HTTPException(401)
        return {
            "healthy": indicator.healthy(),
            "viewers": indicator.viewer_count(),
            "oldestStartedAt": indicator.oldest_started_at(),
        }

    @app.post("/internal/indicator/kill")
    def indicator_kill(request: Request):
        with lifecycle:
            if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
                raise HTTPException(403)
            if not indicator.authenticate(request.headers.get("x-watchport-indicator", "")):
                raise HTTPException(401)
            failures = 0
            for session in sessions.streaming():
                if not revoke_stream(session, reason="local_kill", close_session=True):
                    failures += 1
            if adapter.uncertain:
                # Failed admission can leave an upstream slot without a local
                # STREAMING session. The host kill control must cover it too.
                recover_slots()
                if not runtime["adapterHealthy"]:
                    raise HTTPException(503, "Viewer-slot cleanup remains unresolved")
                failures = 0
            if failures:
                raise HTTPException(503, f"{failures} stream(s) could not be confirmed revoked")
            return {"ok": True}


    # Expose internals only to tests/integration harnesses, never through HTTP.
    app.state.watchport = {
        "settings": settings,
        "sessions": sessions,
        "indicator": indicator,
        "adapter": adapter,
        "store": store,
    }
    return app


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, proxy_headers=False)


if __name__ == "__main__":
    main()
