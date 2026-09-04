from __future__ import annotations

import json
import sys

from .config import Settings
from .stream_adapter import MoonlightWebAdapter, StreamAdapterError


def _adapter(settings: Settings) -> MoonlightWebAdapter:
    return MoonlightWebAdapter(
        control_origin=settings.moonlight_origin,
        stream_origin=settings.stream_origin,
        slots=settings.moonlight_slots,
        host_uuid=settings.moonlight_host_uuid,
        app_id=settings.moonlight_app_id,
        ttl_seconds=settings.moonlight_ttl_seconds,
        verify_tls=settings.moonlight_verify_tls,
    )


def main() -> None:
    try:
        settings = Settings.from_env()
    except Exception as exc:
        print(f"CONFIG: FAIL — {exc}", file=sys.stderr)
        raise SystemExit(2)

    print("CONFIG: OK")
    print(f"  Watchport origin: {settings.origin}")
    print(f"  Stream origin:    {settings.stream_origin}")
    print(f"  Moonlight control:{settings.moonlight_origin}")
    print(f"  Dedicated slots:  {','.join(map(str, settings.moonlight_slots))}")
    print(f"  Host/app set:     {'yes' if settings.stream_configured else 'no'}")

    adapter = _adapter(settings)
    try:
        probe = adapter.probe()
    except StreamAdapterError as exc:
        print(f"MOONLIGHT CONTROL: FAIL — {exc}", file=sys.stderr)
        raise SystemExit(3)

    print("MOONLIGHT CONTROL: OK")
    share = probe.get("share", {})
    slots = share.get("slots", []) if isinstance(share, dict) else []
    for item in slots:
        if item.get("slot") in settings.moonlight_slots:
            perms = item.get("permissions", {})
            print(
                f"  slot {item.get('slot')}: {item.get('state')} · "
                f"{item.get('access_level')} · input="
                f"{bool(perms.get('gamepad') or perms.get('keyboardMouse'))}"
            )

    hosts = probe.get("hosts", [])
    if isinstance(hosts, dict):
        hosts = hosts.get("hosts", hosts.get("data", []))
    print("PAIRED HOSTS:")
    if not isinstance(hosts, list) or not hosts:
        print("  none returned — pair Sunshine in Moonlight-Web first")
    else:
        for host in hosts:
            uuid = host.get("uuid") or host.get("id") or host.get("host_id")
            name = host.get("name") or host.get("hostname") or "unnamed"
            state = host.get("state") or host.get("pairState") or host.get("pair_state") or "unknown"
            print(f"  {uuid}  {name}  [{state}]")

    if settings.moonlight_host_uuid:
        try:
            apps = adapter.apps_for(settings.moonlight_host_uuid)
        except StreamAdapterError as exc:
            print(f"APPS: FAIL — {exc}", file=sys.stderr)
            raise SystemExit(4)
        if isinstance(apps, dict):
            apps = apps.get("apps", apps.get("data", []))
        print("APPS FOR CONFIGURED HOST:")
        if isinstance(apps, list):
            for app in apps:
                app_id = app.get("id") or app.get("appId") or app.get("app_id")
                name = app.get("name") or app.get("appName") or "unnamed"
                print(f"  {app_id}  {name}")
        else:
            print(json.dumps(apps, indent=2, sort_keys=True))

    print("\nDoctor completed without changing any Viewer slot.")


if __name__ == "__main__":
    main()
