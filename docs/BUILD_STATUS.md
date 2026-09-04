# Build status

## Implemented

- Installable Python 3.12 package.
- FastAPI gateway with no generated API docs.
- SQLite passkey credential storage.
- WebAuthn registration and authentication.
- Passkey enrollment restricted to localhost.
- Secure/HttpOnly/SameSite session cookie support.
- Per-session CSRF token for state-changing viewer actions.
- Explicit authenticated -> admitted -> streaming -> closed state machine.
- Separate host-side indicator process with authenticated localhost heartbeat.
- Admission fails when the indicator is not healthy.
- Browser UI for enrollment, passkey unlock, viewer start/stop, and viewer count.
- Configurable external viewer URL intended only for a backend-enforced Moonlight-Web Viewer invitation.
- Negative unit tests for admission expiry, indicator liveness, session closure, and viewer counting.

## Security blocker before calling this production-ready

The current external-viewer adapter can gate disclosure/opening of a Moonlight-Web Viewer invitation, but Watchport does not yet own a reliable revocation primitive for that external invitation. If the local indicator heartbeat disappears after the external stream has already connected, the gateway can fail closed internally but cannot yet prove it terminated the Moonlight-Web stream.

This means the strongest invariant — `indicator disappears -> active stream terminates` — is not complete until the stream adapter gains an explicit revoke/stop operation and the gateway invokes it on heartbeat failure/session expiry.

Do not describe the current build as production-ready until that is implemented and tested against the real Moonlight-Web/Sunshine stack.

## Locally verified

The pure state-machine/indicator test slice currently passes 5 tests under Python 3.12. The execution environment used for this bootstrap did not have network access to install the `webauthn` package, so a full live WebAuthn browser integration test still needs to be run on a development machine with dependencies installed.
