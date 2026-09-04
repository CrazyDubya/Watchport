# Security Model

Watchport intentionally exposes one sensitive capability: viewing the pixels currently displayed on a host desktop.

That is already a high-value capability. The project therefore avoids bundling unrelated remote-administration authority.

## Protected assets

Primary assets:

- live desktop pixels
- identity of authorized viewers
- WebAuthn credential metadata
- authenticated session state
- private-network reachability
- accurate host knowledge that viewing is occurring

Explicitly out of scope for V1:

- keyboard/mouse authority
- files
- clipboard
- shell
- arbitrary process execution
- microphone
- power controls

## Threats

### Stolen or unattended client device

Mitigation:

- Tailscale device/network admission is insufficient by itself
- require WebAuthn/passkey authentication
- keep stream admission grants short-lived
- avoid long-lived bearer tokens

### Compromised viewer webpage/browser context

Mitigation:

- do not trust the browser to enforce view-only
- omit generic control APIs from Watchport's gateway/adapter
- enforce viewer/no-input permissions below the UI

### Accidental public exposure

Mitigation:

- private-interface binding by default
- documented Tailscale ACL/Grant policy
- no automatic public fallback
- startup checks should warn/refuse unsafe bind configurations

### Silent viewing

Mitigation:

- persistent host-side indicator
- indicator liveness required for stream admission
- loss of indicator liveness terminates active sessions after a short grace period

### Session theft/replay

Mitigation:

- HTTPS
- Secure + HttpOnly + SameSite cookies
- server-side session validation
- short-lived stream admission
- CSRF protection on state-changing endpoints
- rotate/revoke session identifiers when privilege changes

### Malicious/compromised streaming dependency

Mitigation:

- treat streaming software as a separate component
- expose it only through a narrow adapter
- configure view-only permissions below the browser layer
- do not expose its management/admin interface to remote viewers unless explicitly required and separately authorized

### Malicious local user/process

A fully compromised host can generally capture its own display or alter Watchport. Protecting against an administrator/root compromise on the host is not a V1 goal.

Watchport should still avoid unnecessary privileged execution and protect local IPC against ordinary unprivileged spoofing where practical.

## Required invariants

### INV-1: Private perimeter

The normal Watchport service is not reachable through a public network interface.

### INV-2: Independent authentication

Successful network admission does not imply permission to view. A valid application authentication state is also required.

### INV-3: No remote input

A Watchport viewing session cannot send input/control commands to the host.

### INV-4: Host indication

For every authoritative active viewing session, the host displays persistent viewing state.

### INV-5: Indicator fail-closed

If the gateway cannot verify indicator health, it refuses new sessions and terminates existing sessions after a bounded grace period.

### INV-6: Authorization expiry

Expired or revoked authorization cannot be used to create or silently restore a stream.

## Indicator design

A transient OS notification is insufficient.

Recommended host behavior while active:

- persistent overlay or always-visible window/banner
- tray/menu-bar state
- viewer count
- start time
- local disconnect-all control

A user should not have to remember whether somebody may still be viewing.

## Local IPC

Gateway <-> indicator communication should:

- remain local to the host
- use OS-level permissions and/or mutually authenticated ephemeral secrets
- carry viewer state, not session credentials
- include monotonically changing/expiring liveness state to prevent stale `healthy` state from persisting after crashes

## WebAuthn enrollment

Enrollment is more privileged than authentication.

V1 should favor an explicit local bootstrap ceremony, such as enrollment initiated from the host itself or using a one-time locally displayed bootstrap secret.

Do not allow arbitrary remote clients that merely reach the service to enroll themselves.

## Browser considerations

Test at minimum:

- iOS Safari
- macOS Safari
- Chromium desktop

Test sleep/wake, browser backgrounding, Tailscale path transitions, Wi-Fi <-> cellular transitions, refresh, duplicate tabs, and browser crashes.

## Logging

Recommended audit fields:

- event type
- timestamp
- local session ID (non-secret)
- principal/credential identifier (non-secret stable reference)
- device/network identity when safely available
- outcome/reason code

Never log:

- screen content
- screenshots/video
- cookies
- private keys
- bearer/session secrets
- raw WebAuthn assertion data beyond what is operationally required

## Secure defaults

A default installation should be safer than a customized one.

Examples:

- audio off
- one explicitly enrolled user
- no public bind
- no control functionality
- short stream admission lifetime
- indicator required
- conservative session timeout

## Security regression rule

A feature that requires weakening an invariant is not a routine feature change. It requires an explicit architecture/security decision and documentation of the new threat model.
