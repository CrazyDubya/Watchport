# Roadmap

## Phase 0 — Validate the streaming substrate

Goal: prove that the browser streaming path is viable before building product infrastructure around it.

Deliverables:

- run Sunshine on the target desktop
- select/evaluate a browser-capable Moonlight/WebRTC bridge
- confirm iOS Safari compatibility
- measure end-to-end latency on LAN and remote Tailscale paths
- confirm text readability at 1080p30 and 1440p30
- verify backend-enforced view-only/no-input behavior
- document exact ports/processes/protocols involved

Exit criteria:

- stable browser stream
- no input path available to a viewer account
- acceptable reconnect behavior
- architecture decision recorded

## Phase 1 — Gateway + passkeys

Goal: put an independent application authorization gate in front of stream admission.

Deliverables:

- minimal gateway service
- WebAuthn enrollment ceremony
- WebAuthn authentication
- secure session cookie
- short-lived stream admission grant
- private-interface binding checks
- minimal audit events

Exit criteria:

- tailnet access alone cannot start viewing
- unauthenticated admission requests fail
- expired admission cannot reconnect

## Phase 2 — Host indicator

Goal: make silent viewing impossible during normal operation.

Deliverables:

- host tray/menu-bar state
- persistent visible banner/overlay
- active viewer count
- gateway <-> indicator heartbeat
- fail-closed admission on indicator failure
- bounded teardown when indicator disappears
- local `disconnect all` control

Exit criteria:

- stream cannot start without healthy indicator
- killing indicator terminates active sessions
- stale viewer state clears correctly after crashes

## Phase 3 — Viewer polish

Goal: make opening Watchport feel nearly instantaneous.

Deliverables:

- mobile-first web viewer
- passkey-first UX
- connection state UI
- automatic safe reconnect
- quality profiles
- fullscreen/PWA behavior where supported
- browser background/foreground handling

Exit criteria:

- bookmark -> passkey -> live desktop is fast and reliable
- no hidden control capability is introduced

## Phase 4 — Hardening

Deliverables:

- threat-model review
- dependency audit
- negative/security tests
- safe-bind startup checks
- session revocation
- enrollment recovery design
- deployment documentation for Tailscale Grants/ACLs
- Tailnet Lock/device-posture optional hardening guidance

## Phase 5 — Packaging

Only after the design proves stable:

- simple host installer/setup script
- service startup configuration
- explicit dependency checks
- upgrade path
- backup/recovery of non-secret configuration

Avoid packaging complexity before the security model and streaming substrate are validated.

## Explicitly deferred

These require a new architecture/security decision rather than simply appearing on the roadmap:

- remote keyboard/mouse/touch
- file transfer
- clipboard
- shell/terminal
- microphone
- public cloud relay
- public Internet access
- remote wake/reboot/power controls
- multi-tenant hosted service
