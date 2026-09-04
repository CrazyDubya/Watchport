# Architecture

## Goal

Watchport provides a browser-visible, low-latency, view-only stream of a host desktop over a private Tailscale network with independent passkey authentication and a mandatory host-side viewing indicator.

## Components

### 1. Gateway

Responsibilities:

- terminate HTTPS on the private interface
- perform WebAuthn registration/authentication
- issue short-lived authenticated sessions
- decide whether a stream may start
- track active viewers
- emit audit metadata
- maintain indicator liveness
- coordinate reconnect and teardown

The gateway must not implement desktop capture or video encoding.

### 2. Viewer

A minimal browser application responsible for:

- passkey ceremony UI
- stream status
- media playback
- quality profile selection
- reconnect behavior
- clear local state such as `connecting`, `live`, `reconnecting`, `closed`

The viewer must not expose or send remote-control input.

### 3. Stream adapter

A narrow integration layer between Watchport and the chosen streaming substrate.

Initial candidate stack:

- Sunshine for host capture and hardware encoding
- Moonlight-compatible/browser bridge for stream delivery

The adapter contract should expose only operations required for view-only streaming, for example:

- `start_view(session, profile)`
- `stop_view(session)`
- `health()`

It should not expose generic remote-control methods.

### 4. Host indicator

A local process/UI that displays persistent viewing state.

Minimum interface:

- receive active-viewer state from the gateway through a local-only authenticated channel
- render a persistent visible warning while viewers > 0
- expose health/heartbeat
- optionally expose a local `disconnect all` action

The gateway treats indicator health as an admission dependency.

## Trust boundaries

```text
[ Browser / potentially hostile ]
            |
            | Tailscale + HTTPS + WebAuthn session
            v
[ Gateway / trusted Watchport component ]
       |                         |
       | narrow stream API       | local authenticated channel
       v                         v
[ Streaming substrate ]    [ Host indicator ]
       |
       v
[ Host desktop capture ]
```

The browser is never trusted to self-declare view-only behavior.

The streaming substrate is trusted for pixels/encoding but should be denied unnecessary authority by configuration and adapter design.

## Network model

Default topology:

- no public listener
- no router port forwarding
- no Internet-facing reverse proxy
- no mandatory third-party relay
- browser and host are members of the same authorized tailnet
- Tailscale policy limits which devices/identities can reach the Watchport service

Where possible, bind Watchport to localhost and/or the host Tailscale address only.

## Authentication model

Two gates are intentionally independent:

1. Network admission through Tailscale.
2. User authentication through WebAuthn/passkey.

A valid tailnet connection alone does not create a viewing session.

## Stream admission

A stream may begin only when all are true:

- request arrived through the expected private interface
- browser session is currently authenticated
- stream authorization is unexpired
- host indicator is healthy
- stream adapter reports healthy
- requested profile is policy-valid

Admission failure should provide minimal information externally and sufficient audit detail locally.

## Reconnect model

Reconnection should optimize for speed without turning a stale browser tab into a persistent bearer token.

Recommended distinction:

- authentication session: moderate lifetime
- stream admission grant: short lifetime
- active media session: continuously checked for authorization/indicator liveness

A foregrounded browser may reconnect quickly while the authentication session remains valid, but must obtain a fresh stream admission grant.

## Multi-viewer behavior

Support multiple viewers only if lifecycle accounting is correct.

Indicator state should be derived from authoritative active sessions, not browser-reported presence.

Suggested state:

```text
viewer_count: N
sessions:
  - id
  - authenticated_principal
  - device metadata (if available)
  - started_at
  - last_liveness
```

Do not expose session secrets through the indicator channel.

## Quality profiles

Start with explicit profiles rather than arbitrary user-provided encoder settings.

Suggested initial profiles:

- low-data: 720p, 20-30fps
- balanced: 1080p30
- live: 1080p60
- crisp: 1440p30

Actual bitrate/codec choices should be validated against Safari/iOS and Chrome-class browsers before finalization.

## Deployment direction

Initial target should optimize for a single-user installation on one desktop.

Prefer:

- one small gateway process
- one host indicator process
- existing separately installed streaming software
- Tailscale already installed on host and clients

Avoid containers or orchestration unless they produce a concrete security or deployment benefit.
