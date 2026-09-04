from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock


class AuditLog:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = RLock()

    def event(self, name: str, **fields: object) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": name,
            **{k: v for k, v in fields.items() if v is not None},
        }
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
