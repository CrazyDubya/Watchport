from __future__ import annotations

import os
from pathlib import Path
import secrets
import stat
import sys


class BootstrapToken:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "bootstrap-token"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def ensure(self) -> str:
        if self.path.exists():
            return self.path.read_text(encoding="utf-8").strip()
        token = secrets.token_urlsafe(32)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(self.path, flags, stat.S_IRUSR | stat.S_IWUSR)
        try:
            os.write(fd, (token + "\n").encode())
        finally:
            os.close(fd)
        return token

    def verify(self, supplied: str) -> bool:
        if not supplied or not self.path.exists():
            return False
        expected = self.path.read_text(encoding="utf-8").strip()
        return bool(expected) and secrets.compare_digest(expected, supplied)

    def consume(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def main() -> None:
    from .config import Settings

    settings = Settings.from_env()
    token = BootstrapToken(settings.data_dir).ensure()
    print("Watchport first-passkey bootstrap token:")
    print(token)
    print()
    print("Open Watchport at its configured HTTPS tailnet URL and paste this token once.")
    print(f"Token file: {settings.data_dir / 'bootstrap-token'}", file=sys.stderr)


if __name__ == "__main__":
    main()
