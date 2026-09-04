from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import Settings
from .indicator_state import IndicatorState
from .sessions import SessionManager, State
from .store import CredentialStore
from .webauthn_service import WebAuthnService

COOKIE = "watchport_session"


def _is_loopback(request: Request) -> bool:
    return bool(request.client and request.client.host in {"127.0.0.1", "::1"})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = CredentialStore(settings.data_dir / "watchport.sqlite3")
    auth = WebAuthnService(settings.rp_id, settings.origin, store)
    sessions = SessionManager(settings.session_ttl_seconds, settings.admission_ttl_seconds)
    indicator = IndicatorState(settings.indicator_secret, settings.indicator_timeout_seconds)
    challenges: dict[str, tuple[bytes, float]] = {}

    app = FastAPI(title="Watchport", docs_url=None, redoc_url=None, openapi_url=None)
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), clipboard-read=(), clipboard-write=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-src https: http:; connect-src 'self' https: wss:"
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
        if not secrets.compare_digest(supplied, session.csrf):
            raise HTTPException(403, "CSRF check failed")

    def new_challenge(kind: str) -> tuple[str, bytes]:
        key = secrets.token_urlsafe(24)
        challenge = secrets.token_bytes(32)
        challenges[f"{kind}:{key}"] = (challenge, time.time() + 120)
        return key, challenge

    def take_challenge(kind: str, key: str) -> bytes:
        item = challenges.pop(f"{kind}:{key}", None)
        if not item or time.time() > item[1]:
            raise HTTPException(400, "challenge expired")
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
            "viewers": len(indicator.active_sessions),
            "viewerConfigured": bool(settings.viewer_url),
        }

    @app.post("/api/passkeys/register/options")
    def register_options(request: Request):
        if not _is_loopback(request):
            raise HTTPException(403, "passkey enrollment is localhost-only")
        key, challenge = new_challenge("register")
        return JSONResponse({"challengeKey": key, "options": json.loads(auth.registration_options(challenge))})

    @app.post("/api/passkeys/register/verify")
    async def register_verify(request: Request):
        if not _is_loopback(request):
            raise HTTPException(403, "passkey enrollment is localhost-only")
        body = await request.json()
        auth.verify_registration(body["credential"], take_challenge("register", body["challengeKey"]))
        return {"ok": True}

    @app.post("/api/passkeys/auth/options")
    def authentication_options():
        if store.count() == 0:
            raise HTTPException(409, "no passkey enrolled")
        key, challenge = new_challenge("auth")
        return JSONResponse({"challengeKey": key, "options": json.loads(auth.authentication_options(challenge))})

    @app.post("/api/passkeys/auth/verify")
    async def authentication_verify(request: Request, response: Response):
        body = await request.json()
        auth.verify_authentication(body["credential"], take_challenge("auth", body["challengeKey"]))
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
        return {"ok": True, "csrf": session.csrf}

    @app.post("/api/logout")
    def logout(request: Request, response: Response):
        session = require_session(request)
        require_csrf(request, session)
        if session.state == State.STREAMING:
            indicator.viewer_stop(session.token)
        sessions.close(session)
        response.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    @app.post("/api/view/start")
    def view_start(request: Request):
        session = require_session(request)
        require_csrf(request, session)
        if not settings.viewer_url:
            raise HTTPException(503, "WATCHPORT_VIEWER_URL is not configured")
        if not indicator.healthy():
            raise HTTPException(503, "host indicator is not healthy")
        sessions.admit(session, True)
        sessions.start_stream(session)
        indicator.viewer_start(session.token)
        return {"viewerUrl": settings.viewer_url, "startedAt": session.stream_started_at}

    @app.post("/api/view/stop")
    def view_stop(request: Request):
        session = require_session(request)
        require_csrf(request, session)
        indicator.viewer_stop(session.token)
        sessions.close(session)
        return {"ok": True}

    @app.post("/internal/indicator/heartbeat")
    def indicator_heartbeat(request: Request):
        if not _is_loopback(request):
            raise HTTPException(403, "indicator endpoint is localhost-only")
        if not indicator.authenticate(request.headers.get("x-watchport-indicator", "")):
            raise HTTPException(401, "bad indicator secret")
        indicator.heartbeat()
        return {"viewers": len(indicator.active_sessions)}

    @app.get("/internal/indicator/state")
    def indicator_state(request: Request):
        if not _is_loopback(request):
            raise HTTPException(403)
        if not indicator.authenticate(request.headers.get("x-watchport-indicator", "")):
            raise HTTPException(401)
        return {"healthy": indicator.healthy(), "viewers": len(indicator.active_sessions)}

    return app


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, proxy_headers=False)


if __name__ == "__main__":
    main()
