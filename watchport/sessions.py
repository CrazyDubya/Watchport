from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import secrets
from threading import RLock
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
    viewer_last_seen_at: float = 0


@dataclass
class SessionManager:
    ttl_seconds: int
    admission_ttl_seconds: int
    _sessions: dict[str, Session] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def create(self, now: float | None = None) -> Session:
        now = time.time() if now is None else now
        session = Session(
            token=secrets.token_urlsafe(32),
            csrf=secrets.token_urlsafe(24),
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._sessions[session.token] = session
        return session

    def get(self, token: str | None, now: float | None = None) -> Session | None:
        if not token:
            return None
        now = time.time() if now is None else now
        with self._lock:
            session = self._sessions.get(token)
            if not session or session.state == State.CLOSED:
                return None
            if now >= session.expires_at:
                # Do not remove an expired streaming session here. The watchdog
                # must still see it so the external stream can be revoked first.
                if session.state != State.STREAMING:
                    session.state = State.CLOSED
                    self._sessions.pop(token, None)
                return None
            return session

    def admit(self, session: Session, indicator_healthy: bool, now: float | None = None) -> Session:
        now = time.time() if now is None else now
        with self._lock:
            remaining = session.expires_at - now
            if (
                not indicator_healthy
                or session.state != State.AUTHENTICATED
                or remaining < self.admission_ttl_seconds
            ):
                raise PermissionError("stream admission denied; reauthenticate if the session is near expiry")
            session.state = State.ADMITTED
            session.admitted_until = now + self.admission_ttl_seconds
            return session

    def start_stream(self, session: Session, now: float | None = None) -> Session:
        now = time.time() if now is None else now
        with self._lock:
            if session.state != State.ADMITTED or now >= session.admitted_until or now >= session.expires_at:
                raise PermissionError("stream admission expired")
            session.state = State.STREAMING
            session.stream_started_at = now
            session.viewer_last_seen_at = now
            return session

    def touch_viewer(self, session: Session, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            if session.state != State.STREAMING or now >= session.expires_at:
                raise PermissionError("stream is not active")
            session.viewer_last_seen_at = now

    def stop_stream(self, session: Session) -> None:
        with self._lock:
            if session.state == State.CLOSED:
                return
            session.state = State.AUTHENTICATED
            session.admitted_until = 0
            session.stream_started_at = 0
            session.viewer_last_seen_at = 0

    def close(self, session: Session) -> None:
        with self._lock:
            session.state = State.CLOSED
            self._sessions.pop(session.token, None)

    def streaming(self) -> list[Session]:
        with self._lock:
            return [s for s in self._sessions.values() if s.state == State.STREAMING]

    def all(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())
