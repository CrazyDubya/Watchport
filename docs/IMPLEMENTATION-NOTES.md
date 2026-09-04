# Implementation Notes

These are provisional engineering preferences, not frozen requirements.

## Keep the stack boring

Prefer mature, auditable components and standard protocols.

Reasonable initial choices:

- gateway: small Go, Rust, or similarly self-contained service
- browser UI: minimal TypeScript/vanilla web app; avoid a large frontend framework unless it earns its complexity
- host indicator: native-lightweight implementation appropriate to the host OS
- state: in-memory sessions plus a tiny local persistent credential/config store; do not introduce a network database for a single-user host

## Avoid premature infrastructure

Do not add by default:

- Docker
- Kubernetes
- Redis
- Postgres
- hosted auth
- cloud relay
- message queues
- service mesh
- telemetry SaaS

A single-user host should remain understandable from `ps`, local logs, and a small config directory.

## Protocol contracts

Define narrow internal interfaces before wiring dependencies directly throughout the codebase.

Example conceptual contracts:

```text
Authenticator
  beginRegistration()
  finishRegistration()
  beginAuthentication()
  finishAuthentication()

StreamAdapter
  health()
  startView(session, profile)
  stopView(session)

Indicator
  health()
  setViewerState(viewers)
  disconnectAll()
```

Avoid a generic `execute()` or arbitrary passthrough API.

## Configuration

Configuration should be explicit and safe by default.

Potential settings:

- listen address
- HTTPS certificate mode
- RP ID / origin
- session lifetime
- stream admission lifetime
- indicator heartbeat/grace period
- allowed quality profiles
- audio enabled: false by default
- selected stream adapter

Secrets should not live in source-controlled config.

## Enrollment

The first credential enrollment should require local proof of presence.

Good candidate flow:

1. host starts Watchport
2. local indicator/setup UI shows enrollment is not complete
3. user initiates one-time bootstrap locally
4. browser performs WebAuthn registration
5. bootstrap token is consumed and cannot be reused

Avoid remote open registration.

## HTTPS

WebAuthn requires a secure context outside special localhost cases. A Tailscale/MagicDNS/Tailscale HTTPS approach may be appropriate; validate the deployment UX rather than weakening WebAuthn requirements.

## Testing philosophy

Most security bugs are likely to occur at lifecycle boundaries, not during a stable stream.

Spend disproportionate test effort on:

- reconnects
- crashes
- stale sessions
- duplicated tabs
- indicator restarts
- gateway restarts
- Tailscale network path changes
- expired authorization

A demo that only works when everything stays connected is not enough.
