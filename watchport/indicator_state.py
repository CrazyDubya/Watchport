from __future__ import annotations

from dataclasses import dataclass, field
import hmac
import secrets
from threading import RLock
import time


@dataclass
class IndicatorState:
    secret: str
    timeout_seconds: int
    last_heartbeat: float = 0
    active_sessions: dict[str, float] = field(default_factory=dict)
    display_token: str = field(default_factory=lambda: secrets.token_urlsafe(18))
    rendered_token: str | None = None
    _lock: RLock = field(default_factory=RLock, repr=False)

    def authenticate(self, supplied: str) -> bool:
        return bool(supplied) and hmac.compare_digest(self.secret, supplied)

    def heartbeat(self, now: float | None = None, *, rendered_token: str | None = None) -> None:
        with self._lock:
            self.last_heartbeat = time.time() if now is None else now
            self.rendered_token = rendered_token

    def confirmed(self, session_id: str) -> bool:
        with self._lock:
            return self.healthy() and session_id in self.active_sessions and self.rendered_token == self.display_token

    def snapshot(self) -> dict:
        with self._lock:
            return {"viewers": len(self.active_sessions), "oldestStartedAt": self.oldest_started_at(), "displayToken": self.display_token}

    def _changed(self) -> None:
        self.display_token = secrets.token_urlsafe(18)
        self.rendered_token = None

    def healthy(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            return self.last_heartbeat > 0 and (now - self.last_heartbeat) <= self.timeout_seconds

    def viewer_start(self, session_id: str, now: float | None = None) -> None:
        with self._lock:
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = time.time() if now is None else now
                self._changed()

    def viewer_stop(self, session_id: str) -> None:
        with self._lock:
            if session_id in self.active_sessions:
                self.active_sessions.pop(session_id)
                self._changed()

    def viewer_count(self) -> int:
        with self._lock:
            return len(self.active_sessions)

    def oldest_started_at(self) -> float | None:
        with self._lock:
            return min(self.active_sessions.values()) if self.active_sessions else None

    def clear(self) -> None:
        with self._lock:
            self.active_sessions.clear()
            self._changed()
