from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock


class CredentialStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._lock = RLock()
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS credentials (
                credential_id BLOB PRIMARY KEY,
                public_key BLOB NOT NULL,
                sign_count INTEGER NOT NULL DEFAULT 0,
                label TEXT NOT NULL DEFAULT 'passkey',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._db.commit()

    def count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM credentials").fetchone()[0])

    def all(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT credential_id, public_key, sign_count, label FROM credentials"
            ).fetchall()
        return [
            {"credential_id": r[0], "public_key": r[1], "sign_count": r[2], "label": r[3]}
            for r in rows
        ]

    def get(self, credential_id: bytes) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT credential_id, public_key, sign_count, label FROM credentials WHERE credential_id=?",
                (credential_id,),
            ).fetchone()
        if not row:
            return None
        return {"credential_id": row[0], "public_key": row[1], "sign_count": row[2], "label": row[3]}

    def put(self, credential_id: bytes, public_key: bytes, sign_count: int, label: str = "passkey") -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO credentials(credential_id, public_key, sign_count, label) VALUES(?,?,?,?)",
                (credential_id, public_key, sign_count, label),
            )
            self._db.commit()

    def update_sign_count(self, credential_id: bytes, sign_count: int) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE credentials SET sign_count=? WHERE credential_id=?",
                (sign_count, credential_id),
            )
            self._db.commit()
