from __future__ import annotations

from datetime import datetime
import json
import os
import threading
import time
from urllib.request import Request, urlopen
import tkinter as tk

from .config import Settings
from .stream_adapter import MoonlightWebAdapter, StreamAdapterError


def _gateway_request(base: str, secret: str, path: str, method: str = "GET") -> dict:
    headers = {"X-Watchport-Indicator": secret}
    req = Request(base + path, method=method, headers=headers)
    with urlopen(req, timeout=2) as response:
        return json.loads(response.read())


def _failsafe_adapter(settings: Settings) -> MoonlightWebAdapter:
    return MoonlightWebAdapter(
        control_origin=settings.moonlight_origin,
        stream_origin=settings.stream_origin,
        slots=settings.moonlight_slots,
        host_uuid=settings.moonlight_host_uuid,
        app_id=settings.moonlight_app_id,
        ttl_seconds=settings.moonlight_ttl_seconds,
        verify_tls=settings.moonlight_verify_tls,
    )


def _poll(base: str, secret: str, settings: Settings, state: dict, stop: threading.Event):
    disconnected_since: float | None = None
    last_failsafe = 0.0
    adapter = _failsafe_adapter(settings)
    while not stop.is_set():
        now = time.time()
        try:
            data = _gateway_request(base, secret, "/internal/indicator/heartbeat", "POST")
            state["viewers"] = int(data.get("viewers", 0))
            state["oldest"] = data.get("oldestStartedAt")
            state["healthy"] = True
            state["failsafe"] = False
            disconnected_since = None
        except Exception:
            state["healthy"] = False
            if disconnected_since is None:
                disconnected_since = now
            # If the gateway disappears, the indicator becomes the second,
            # independent revoker. It owns the same dedicated Moonlight slots and
            # kills all of them directly after a short grace period.
            if now - disconnected_since >= settings.indicator_timeout_seconds and now - last_failsafe >= 5:
                last_failsafe = now
                try:
                    adapter.cleanup_stale_slots()
                    state["viewers"] = 0
                    state["oldest"] = None
                    state["failsafe"] = True
                except StreamAdapterError:
                    state["failsafe"] = False
        stop.wait(2)


def _kill(base: str, secret: str, state: dict) -> None:
    try:
        _gateway_request(base, secret, "/internal/indicator/kill", "POST")
        state["viewers"] = 0
        state["oldest"] = None
    except Exception:
        state["healthy"] = False


def main() -> None:
    settings = Settings.from_env()
    base = os.getenv("WATCHPORT_LOCAL_URL", f"http://127.0.0.1:{settings.port}").rstrip("/")
    secret = settings.indicator_secret

    state = {"viewers": 0, "healthy": False, "oldest": None, "failsafe": False}
    stop = threading.Event()
    threading.Thread(
        target=_poll, args=(base, secret, settings, state, stop), daemon=True
    ).start()

    root = tk.Tk()
    root.title("Watchport")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    frame = tk.Frame(root, padx=16, pady=12)
    frame.pack()
    label = tk.Label(frame, text="Watchport indicator starting…", font=("Arial", 12, "bold"))
    label.pack()
    detail = tk.Label(frame, text="", font=("Arial", 9))
    detail.pack(pady=(4, 0))
    kill_button = tk.Button(frame, text="Disconnect viewers", command=lambda: _kill(base, secret, state))
    kill_button.pack(pady=(9, 0))

    def refresh():
        viewers = state["viewers"]
        if viewers > 0:
            label.config(text=f"● DESKTOP IS BEING VIEWED — {viewers} viewer{'s' if viewers != 1 else ''}")
            oldest = state.get("oldest")
            if oldest:
                elapsed = max(0, int(time.time() - float(oldest)))
                detail.config(text=f"Active for {elapsed // 60}:{elapsed % 60:02d} · local kill available")
            else:
                detail.config(text="Active remote viewing · local kill available")
            kill_button.pack(pady=(9, 0))
            root.deiconify()
        elif not state["healthy"]:
            label.config(text="WATCHPORT CONTROL PLANE DISCONNECTED")
            detail.config(
                text="Failsafe revoked Viewer slots" if state.get("failsafe") else "Attempting direct Viewer-slot revocation…"
            )
            kill_button.pack_forget()
            root.deiconify()
        else:
            label.config(text="Watchport ready")
            detail.config(text=datetime.now().strftime("Indicator healthy · %H:%M:%S"))
            kill_button.pack_forget()
            root.withdraw()
        root.after(500, refresh)

    def close():
        # Closing the indicator intentionally makes the gateway's heartbeat test
        # fail; its watchdog will revoke every active viewer before allowing any
        # new admission.
        stop.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
