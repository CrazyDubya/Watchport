# AGENTS.md

This file defines the operating rules for coding agents working on Watchport.

## Mission

Build the smallest practical system that lets an authenticated user securely **view** a live desktop in a browser over a private Tailscale network with very low latency and a persistent host-side warning.

Watchport is intentionally not a general remote-access suite.

## Non-negotiable security invariants

Do not merge code that violates any of these:

1. **Private-network-only exposure.** No public bind address, public relay, public ingress, or router port-forward is required by default.
2. **Passkey required.** Tailnet access alone does not authorize viewing.
3. **No control channel.** V1 must not permit keyboard, mouse, touch, clipboard, file transfer, shell, arbitrary commands, or remote application launching.
4. **Host awareness.** Every active viewer must produce a persistent local indication for the duration of the viewing session.
5. **Fail closed.** If viewer authorization expires, indicator heartbeat fails, or session state becomes ambiguous, terminate viewing.
6. **Least privilege.** Components should run with the minimum OS/network privileges needed.
7. **Explicit trust boundaries.** Never assume a browser, streaming bridge, Sunshine, or Tailscale identity is sufficient on its own.

## Development priorities

Use this ordering when tradeoffs arise:

1. security invariant preservation
2. simplicity / small trusted computing base
3. correctness
4. low latency
5. reliable reconnect behavior
6. cross-platform portability
7. polish

## Architecture rules

Prefer separate components with narrow contracts:

- `gateway`: passkeys, sessions, viewer admission, audit events
- `viewer`: browser UI and media presentation only
- `indicator`: host-side persistent viewer state UI
- `stream-adapter`: narrowly scoped integration with the selected streaming substrate

Do not collapse these into a single privileged daemon merely for convenience.

## Streaming substrate

Do **not** implement desktop capture, hardware encoding, codecs, congestion control, or NAT traversal from scratch unless an architectural review demonstrates there is no acceptable mature component.

Initial research target:

- Sunshine for capture/encoding
- a Moonlight/browser/WebRTC bridge for browser delivery
- Tailscale for network reachability

Treat all three as replaceable dependencies behind interfaces.

## View-only enforcement

View-only must be enforced below the UI layer.

It is insufficient to:

- hide buttons
- ignore pointer events in CSS
- omit JavaScript event handlers
- trust a viewer role sent by the browser

Agents must identify where input messages could enter the streaming stack and ensure they are rejected or absent server-side.

Whenever possible, configure the streaming bridge with a backend-enforced viewer role and additionally disable/omit input forwarding in Watchport's own adapter.

## Authentication

Use WebAuthn/passkeys. Do not invent password authentication unless required solely as a local recovery mechanism and separately threat-modeled.

Requirements:

- challenge-based WebAuthn
- verified origin / RP ID
- secure, HttpOnly, SameSite cookies for authenticated browser sessions
- CSRF protection where state-changing HTTP endpoints exist
- short-lived authorization to begin viewing
- explicit reauthentication policy for stale sessions
- credentials stored with least sensitive material possible; private keys remain in authenticators

Enrollment is a distinct privileged operation from ordinary viewing.

## Tailscale assumptions

The normal deployment model is:

- service binds to localhost and/or its Tailscale interface only
- tailnet policy restricts which identities/devices can reach the Watchport port
- no public DNS requirement
- no router port forwarding

Do not silently add fallback public ingress.

Tailscale improves the perimeter but is not a substitute for application authentication.

## Host indicator

The indicator is a security control, not decoration.

Minimum behavior:

- visible while one or more viewers are active
- viewer count if known
- connection start time
- clear wording such as `DESKTOP IS BEING VIEWED`
- local tray/menu-bar state in addition to an on-screen indication where practical
- local disconnect/kill action may be added even though remote control is out of scope

The gateway and indicator must maintain an authenticated/local-only liveness relationship. If the indicator cannot prove it is functioning, new streams must not start and existing streams should terminate after a short grace period.

## Session lifecycle

Model sessions explicitly. Suggested states:

`unauthenticated -> authenticated -> admitted -> streaming -> closing -> closed`

Unexpected transitions fail closed.

A browser refresh, sleep/wake, network switch, or Tailscale path change must not result in a second uncontrolled stream or stale indicator state.

## Logging and privacy

Audit metadata, not desktop content.

Useful events:

- passkey authentication success/failure
- viewer admitted/rejected
- stream start/stop
- viewer device identity when available
- indicator heartbeat failure
- authorization expiration

Do not record screenshots, video, window titles, clipboard content, or keystrokes.

Never log WebAuthn challenges, session secrets, cookies, private keys, or raw authentication tokens.

## Dependency and licensing policy

Watchport original code is MIT unless explicitly documented otherwise.

Do not copy or vendor GPL code into MIT-licensed Watchport components without stopping and documenting the licensing consequence.

Prefer process/network/runtime integration with GPL dependencies when practical. External software keeps its original license.

Before adding a dependency:

1. identify its exact license
2. confirm redistribution/integration implications
3. record it in `docs/LICENSING.md`
4. pin or constrain versions appropriately
5. avoid abandoned security-critical dependencies when a maintained alternative exists

## Agent workflow

Before coding:

1. read README.md
2. read docs/SECURITY.md
3. read docs/ARCHITECTURE.md
4. inspect existing tests and open issues
5. identify which security invariant(s) the change touches

For each meaningful change:

- state the intended behavior
- state the trust boundary affected
- add or update tests
- run the narrowest relevant tests first, then the full suite
- document any remaining uncertainty

Do not make broad refactors during a security-sensitive feature unless required.

## Testing expectations

Prefer automated tests for invariants rather than only happy-path behavior.

Important negative tests include:

- unauthenticated client cannot request stream admission
- authenticated but non-tailnet/untrusted path is rejected by deployment policy
- expired session cannot reconnect silently
- malformed input-control messages are rejected
- viewer cannot invoke input APIs
- indicator failure prevents admission
- indicator disappearance terminates an active stream
- second viewer increments indicator state correctly
- disconnect decrements viewer count correctly
- browser crash eventually clears session/indicator state

## Security review trigger

Stop normal implementation and perform an explicit mini-review before adding any feature involving:

- remote input
- clipboard
- files
- audio capture/microphone
- command execution
- wake/reboot/power actions
- public ingress
- cloud relay
- multi-user sharing
- password fallback
- persistent bearer tokens

These are outside V1 by default.

## Scope discipline

A feature is not automatically desirable because Sunshine, Moonlight, WebRTC, or the OS makes it easy.

The core question is always:

> Does this make secure, immediate, view-only desktop observation materially better without broadening authority?

If not, leave it out.
