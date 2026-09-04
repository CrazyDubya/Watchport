from __future__ import annotations

from dataclasses import dataclass, field
import hmac
import time


@dataclass
class IndicatorState:
    secret: str
    timeout_seconds: int
    last_heartbeat: float = 0
    active_sessions: set[str] = field(default_factory=set)

    def authenticate(self, supplied: str) -> bool:
        return bool(supplied) and hmac.compare_digest(self.secret, supplied)

    def heartbeat(self, now: float | None = None) -> None:
        self.last_heartbeat = time.time() if now is None else now

    def healthy(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self.last_heartbeat > 0 and (now - self.last_heartbeat) <= self.timeout_seconds

    def viewer_start(self, session_id: str) -> None:
        self.active_sessions.add(session_id)

    def viewer_stop(self, session_id: str) -> None:
        self.active_sessions.discard(session_id)
