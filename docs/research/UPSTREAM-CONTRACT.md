# Streaming contract inspection — 2026-09-10

This is source inspection, **not a live streaming benchmark or adoption acceptance**.

| Component | Source/version inspected | Integration |
|---|---|---|
| Moonlight-Web | `linckosz/moonlight-web`, `ff98a358a6bb53340d2b33b4bdf0f7a72311a12d` | Separately installed service; upstream README declares GPL-3.0 and LICENSE contains GPL v3; no source copied |
| Sunshine | Official current getting-started documentation | Separately installed capture/encode service; target binary/version still to record |
| Tailscale | Official Serve CLI documentation | Installed private networking/HTTPS; target version still to record |

Confirmed Moonlight API observations:

- `/api/share/slots/:n/deactivate` stops the player worker and returns slot state. Watchport now requires the requested slot and `state=off`, including when other slots failed.
- `/api/internet/status` includes `internet_access_enabled`. `local_only=true` on an invitation only describes its current link path; a disconnected rendezvous could otherwise mask an enabled public mode. Watchport now explicitly checks the configured switch before minting.
- The player role has `gamepad=false` and `keyboardMouse=false`, with policy enforced below the UI. Live hostile-input testing is still required.
- Share TTL whitelist starts at 3600 seconds. Normal Watchport authorization is 900 seconds, so active revocation and process supervision are essential; the upstream TTL alone is not the short Watchport session deadline.
- Player join permits heights 720/1080/1440 and presents a Join screen. The outer iframe does not expose a documented first-frame event or quality-control messaging contract to Watchport.
- A running owner session can override supplied host/app selection. The returned activation omits those identifiers. This is a remaining Desktop-identity verification gap.
- The project now includes a native macOS capture engine. Watchport has not adopted or measured that alternative; retain Sunshine for the current integration unless a separate decision and validation report justifies a change.
- Generic loopback reverse proxying can affect management trust. Player-only ingress is a blocking requirement; see `../PLAYER-INGRESS.md`.

Sources: [ShareRoutes](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/backend/src/server/routes/ShareRoutes.cpp), [InternetAccessManager](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/backend/src/network/InternetAccessManager.cpp), [HTTP guard](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/backend/src/server/HttpServer.cpp), [player UI](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/frontend/js/ui/PlayerJoinView.js), [license](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/LICENSE).
