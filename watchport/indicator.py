from __future__ import annotations

import json
import os
import threading
from urllib.request import Request, urlopen
import tkinter as tk


def _poll(base: str, secret: str, state: dict, stop: threading.Event):
    headers = {"X-Watchport-Indicator": secret}
    while not stop.is_set():
        try:
            req = Request(base + "/internal/indicator/heartbeat", method="POST", headers=headers)
            with urlopen(req, timeout=2) as response:
                data = json.loads(response.read())
                state["viewers"] = int(data.get("viewers", 0))
                state["healthy"] = True
        except Exception:
            state["healthy"] = False
            state["viewers"] = 0
        stop.wait(2)


def main() -> None:
    base = os.getenv("WATCHPORT_LOCAL_URL", "http://127.0.0.1:8443").rstrip("/")
    secret = os.environ.get("WATCHPORT_INDICATOR_SECRET", "")
    if not secret:
        raise SystemExit("WATCHPORT_INDICATOR_SECRET is required")

    state = {"viewers": 0, "healthy": False}
    stop = threading.Event()
    threading.Thread(target=_poll, args=(base, secret, state, stop), daemon=True).start()

    root = tk.Tk()
    root.title("Watchport")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    label = tk.Label(root, text="Watchport indicator starting…", padx=18, pady=10, font=("Arial", 12, "bold"))
    label.pack()

    def refresh():
        viewers = state["viewers"]
        if viewers > 0:
            label.config(text=f"● DESKTOP IS BEING VIEWED — {viewers} viewer{'s' if viewers != 1 else ''}")
            root.deiconify()
        else:
            label.config(text="Watchport ready" if state["healthy"] else "Watchport indicator disconnected")
            root.withdraw() if state["healthy"] else root.deiconify()
        root.after(500, refresh)

    def close():
        stop.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
