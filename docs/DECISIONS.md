# Architecture Decision Log

Use this file for concise decisions that materially affect Watchport's trust model, interoperability, or deployment.

## ADR-0001 — Watchport is view-only by architecture

**Status:** Accepted

Watchport V1 does not provide remote keyboard, mouse, touch, clipboard, file, shell, microphone, power, or arbitrary command capabilities.

Rationale: the product goal is rapid observation, and excluding control authority substantially reduces attack surface and accidental privilege growth.

## ADR-0002 — Tailscale is perimeter, not authentication

**Status:** Accepted

Tailscale provides private reachability and device/identity policy. Watchport independently requires WebAuthn/passkey authentication before stream admission.

## ADR-0003 — Reuse mature streaming components

**Status:** Accepted in principle; substrate selection pending validation

Do not implement screen capture, video codecs, hardware encode, or congestion control from scratch. Sunshine is the initial capture/encode candidate. A browser-capable Moonlight/WebRTC bridge must be experimentally validated before becoming a hard dependency.

## ADR-0004 — Host indicator is part of authorization

**Status:** Accepted

The viewing indicator is a security control, not informational decoration. A healthy indicator is required to admit a viewer. Loss of indicator liveness causes stream teardown after a bounded grace period.

## ADR-0005 — Original Watchport code is MIT

**Status:** Accepted

Original Watchport code is MIT licensed. Strong-copyleft dependencies should remain clearly separated runtime components unless there is an explicit reason to create or distribute a derivative work under compatible terms.

## ADR-0006 — Warning render acknowledgment gates capability release

**Status:** Implemented; physical macOS acceptance pending (2026-09-10)

Reserve warning state, wait for the GUI thread to acknowledge a fresh revision, then mint a Viewer capability and recheck authorization. Network-thread liveness alone is insufficient. A stalled GUI stops heartbeats. Revocation uncertainty retains warning state and blocks admission. This is not proof of visibility above OS lock screens or every fullscreen Space.

## ADR-0007 — Keep owner control behind a player-only boundary

**Status:** Required; target ingress implementation pending

Watchport :8443 and player :9443 use the same hostname but distinct origins. Cookies cross ports, so player ingress must strip owner/Watchport cookies. Never expose the full Moonlight localhost API via a proxy that makes remote requests appear local. Pin and validate an exact upstream version. Existing owner streams can override the requested Desktop; strict identity verification is a remaining upstream contract requirement.

**Deployment update, 2026-09-11:** the project owner assigned HTTPS :9443 to the player to preserve existing routes on :443 and :10000. Watchport remains HTTPS :8443 → loopback :8787; the player-only proxy is reserved on loopback :8788. Intended viewer devices need tailnet access to TCP :8443 and :9443. Direct media ports remain subject to the separately verified media topology.

## ADR-0008 — Phone backgrounding ends viewing intent

**Status:** Implemented; Safari acceptance pending

Background/page exit clears the embedded viewer and requests revocation. Foreground return requires a deliberate View action. Only foreground network failures receive bounded retries, each following confirmed revocation. Authentication or authorization failures do not automatically retry. Displayed access-grant timing must not be labeled video latency.

## ADR-0009 — Independent Mac user LaunchAgents, with explicit limits

**Status:** Prepared, not accepted for unattended use

Generate separate gateway and indicator LaunchAgents for the logged-in Aqua session, loading a private config file without secrets in arguments. KeepAlive restart reduces recovery time but does not prove fail-closed behavior after simultaneous death, logout or a surviving upstream stream. Those cases block unattended readiness until observed and fixed. The installer does not install capture dependencies or alter network policy.

## ADR-0010 — Evidence gates readiness

**Status:** Implemented recorder; measurements pending

Require all security cases and at least five latency samples on each of LAN, cellular and remote networks. Initial p95 targets are 2.5 s to first useful frame, 150 ms LAN / 300 ms remote glass-to-glass, and 5 s reconnect. These are provisional engineering targets, not achieved results or user-specified guarantees; record the reason for any change. Never infer first-frame time from authorization or iframe load.
