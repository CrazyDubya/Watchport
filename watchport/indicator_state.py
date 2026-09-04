from __future__ import annotations

from dataclasses import dataclass, field
import hmac
from threading import RLock
import time


@dataclass
class IndicatorState:
    secret: str
    timeout_seconds: int
    last_heartbeat: float = 0
    active_sessions: dict[str, float] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def authenticate(self, supplied: str) -> bool:
        return bool(supplied) and hmac.compare_digest(self.secret, supplied)

    def heartbeat(self, now: float | None = None) -> None:
        with self._lock:
            self.last_heartbeat = time.time() if now is None else now

    def healthy(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            return self.last_heartbeat > 0 and (now - self.last_heartbeat) <= self.timeout_seconds

    def viewer_start(self, session_id: str, now: float | None = None) -> None:
        with self._lock:
            self.active_sessions.setdefault(session_id, time.time() if now is None else now)

    def viewer_stop(self, session_id: str) -> None:
        with self._lock:
            self.active_sessions.pop(session_id, None)

    def viewer_count(self) -> int:
        with self._lock:
            return len(self.active_sessions)

    def oldest_started_at(self) -> float | None:
        with self._lock:
            return min(self.active_sessions.values()) if self.active_sessions else None

    def clear(self) -> None:
        with self._lock:
            self.active_sessions.clear()
