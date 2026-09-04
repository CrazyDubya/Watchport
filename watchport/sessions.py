from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import secrets
import time


class State(StrEnum):
    AUTHENTICATED = "authenticated"
    ADMITTED = "admitted"
    STREAMING = "streaming"
    CLOSED = "closed"


@dataclass
class Session:
    token: str
    csrf: str
    created_at: float
    expires_at: float
    state: State = State.AUTHENTICATED
    admitted_until: float = 0
    stream_started_at: float = 0


@dataclass
class SessionManager:
    ttl_seconds: int
    admission_ttl_seconds: int
    _sessions: dict[str, Session] = field(default_factory=dict)

    def create(self, now: float | None = None) -> Session:
        now = time.time() if now is None else now
        session = Session(
            token=secrets.token_urlsafe(32),
            csrf=secrets.token_urlsafe(24),
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self._sessions[session.token] = session
        return session

    def get(self, token: str | None, now: float | None = None) -> Session | None:
        if not token:
            return None
        now = time.time() if now is None else now
        session = self._sessions.get(token)
        if not session or session.state == State.CLOSED or now >= session.expires_at:
            if session:
                session.state = State.CLOSED
                self._sessions.pop(token, None)
            return None
        return session

    def admit(self, session: Session, indicator_healthy: bool, now: float | None = None) -> Session:
        if not indicator_healthy or session.state != State.AUTHENTICATED:
            raise PermissionError("stream admission denied")
        now = time.time() if now is None else now
        session.state = State.ADMITTED
        session.admitted_until = min(session.expires_at, now + self.admission_ttl_seconds)
        return session

    def start_stream(self, session: Session, now: float | None = None) -> Session:
        now = time.time() if now is None else now
        if session.state != State.ADMITTED or now >= session.admitted_until:
            raise PermissionError("stream admission expired")
        session.state = State.STREAMING
        session.stream_started_at = now
        return session

    def close(self, session: Session) -> None:
        session.state = State.CLOSED
        self._sessions.pop(session.token, None)
