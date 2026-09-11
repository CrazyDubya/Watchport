# Required player ingress boundary

Status: **integration blocker until implemented and tested on the target stack**.

Watchport :8443 and the player origin :9443 share a hostname so the host-scoped `mw_player` cookie can cross ports. Cookies are not isolated by port: the ingress must strip Watchport/owner cookies before forwarding. Keep the player a different origin (port) from Watchport so its iframe cannot access the parent application DOM.

The agreed host layout reserves `127.0.0.1:8787` for the gateway and `127.0.0.1:8788` for the player-only proxy. Serve HTTPS :8443 targets the gateway; HTTPS :9443 will target the validated proxy. Preserve the existing Serve routes on :443 and :10000. The assigned player port does not change Moonlight's loopback management origin.

Do not point Tailscale Serve at the entire Moonlight management listener. `HttpServer::processRequest` and `RequestGuard` can grant localhost privileges based on the reverse proxy's peer address/Host. Preserving or rewriting Host alone is not an adequate security boundary.

The target Mac agent must implement and validate one of:

- A narrow player proxy on loopback, exposed through Serve, allowing only the installed player's required assets, player APIs and player WebSockets; or
- A verified tailnet-only TLS listener preserving the original remote peer with management/owner routes denied independently of its viewer UI.

Requirements for a proxy:

- Default deny. No `/api/admin/*`, `/api/auth/*`, `/api/hosts/*`, `/api/share/slots/*`, `/api/internet/*`, `/api/system/*`, generic command/control APIs or owner WebSockets (`/ws`, `/ws0`, `/ws1`, `/control`).
- Pin an exact upstream commit and enumerate static paths from its build. Allow only necessary GET/HEAD assets, `/p/<token>`, GET `/api/share/player/info`, POST `/api/share/player/join` and `/leave`, plus verified player signaling/media. PIN redemption is performed locally by Watchport, so no remote PIN API is needed.
- At the inspected upstream commit, player WebSockets are `/ws2`–`/ws4` and their `/stream` subpaths; the upstream cookie must be verified for the matching slot. Determine any required ICE config paths from the actual client. Do not broaden to an API wildcard when an asset or negotiation request fails.
- Forward only `mw_player`, never `watchport_session`, `mw_session`, admin keys, forged proxy headers or arbitrary Authorization. Reject unexpected Set-Cookie names, redirects and absolute-URL proxy targets. Do not log player token paths or query strings.
- Reject encoded path traversal, path normalization tricks, unexpected methods, owner-cookie attempts and cross-origin state changes. Verify backend Viewer permissions still reject normal input protocol messages.
- HTTP ingress isolation does not isolate direct UDP media: restrict every verified media port to authorized tailnet peers, and prevent alternate LAN/public management paths to the streaming service.

The source currently permits an existing owner stream to override the host/app supplied when activating a player slot; its activation response does not identify the selected host/app. Use a dedicated instance without unrelated owner viewing, then test the wrong-host case. A strict unattended deployment needs an upstream contract that allows Watchport to verify/force the intended Desktop before capability release. Do not silently accept another window/game/host.

Evidence: [upstream HTTP guard](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/backend/src/server/HttpServer.cpp), [player routes](https://github.com/linckosz/moonlight-web/blob/ff98a358a6bb53340d2b33b4bdf0f7a72311a12d/backend/src/server/routes/ShareRoutes.cpp).
