# Live acceptance checklist

Watchport is not considered deployment-ready on a host until these tests pass on that exact system and browser/device combination.

Record the date, Watchport commit, Sunshine version, Moonlight-Web version, Tailscale version, host OS, client device/browser, and network path for the run.

## A. Baseline

- [ ] `pytest` passes from a fresh virtual environment.
- [ ] `watchport-doctor` reports Moonlight control healthy.
- [ ] The configured host UUID is the intended Sunshine host.
- [ ] The configured app ID is the intended Desktop/session app.
- [ ] Moonlight-Web Internet Access/rendezvous is disabled.
- [ ] Watchport gateway binds only to loopback.
- [ ] No router port forward exists for Watchport, Moonlight-Web, Sunshine, or WebRTC.
- [ ] Tailscale Funnel is not configured.
- [ ] Tailnet policy grants only the required clients and verified ports.

## B. Network perimeter

From an allowed tailnet client:

- [ ] Watchport HTTPS loads.
- [ ] Moonlight player path loads only after Watchport admission.

From a device not admitted by the tailnet policy:

- [ ] Watchport is unreachable.
- [ ] Moonlight player signaling is unreachable.
- [ ] Verified media ports are unreachable.

From the public internet with Tailscale disconnected:

- [ ] Watchport is unreachable.
- [ ] Moonlight-Web is unreachable.
- [ ] No DNS/port-forward path accidentally exposes either service.

## C. Passkeys

- [ ] First-passkey enrollment works over the real tailnet HTTPS hostname.
- [ ] A wrong/missing bootstrap token cannot obtain registration options.
- [ ] The bootstrap token disappears after first successful enrollment.
- [ ] Reusing the bootstrap token fails.
- [ ] Normal authentication requires user verification (Face ID/Touch ID/Windows Hello/security key as applicable).
- [ ] Canceling platform authentication does not create a session.
- [ ] Authentication from a different origin/RP fails.
- [ ] A second passkey can be added only from an already authenticated session.
- [ ] Logout invalidates the Watchport session.
- [ ] A stale session cannot silently revive a stream.

## D. Structural view-only enforcement

Start a view and verify Moonlight-Web reports the active player as `viewer` with:

- [ ] `gamepad=false`
- [ ] `keyboardMouse=false`

Then actively try to control the host:

- [ ] mouse clicks/movement do nothing
- [ ] physical keyboard input in the viewer does nothing
- [ ] touch/tap gestures do not inject host input
- [ ] gamepad input does nothing
- [ ] clipboard APIs do not create a control path
- [ ] browser developer tools cannot turn control on merely by changing the Watchport DOM/JavaScript

If changing only client-side code can cause host input, **stop: acceptance fails**.

## E. Host warning

- [ ] No view can start before the indicator heartbeat is healthy.
- [ ] Starting a view makes the host warning visible before the remote browser receives a usable stream.
- [ ] Warning text clearly says the desktop is being viewed.
- [ ] Viewer count is correct for one viewer.
- [ ] Viewer count increments/decrements correctly for multiple sessions.
- [ ] Elapsed time is plausible.
- [ ] The warning remains on top during ordinary host activity.
- [ ] Local **Disconnect viewers** kills every Watchport viewer.

## F. Kill-path tests

These are mandatory.

### Kill the indicator

With a live stream:

- [ ] terminate `watchport-indicator`
- [ ] gateway notices the missing heartbeat
- [ ] underlying Moonlight Viewer slot is deactivated
- [ ] remote video stops
- [ ] expected target: stream authority gone within roughly 8 seconds
- [ ] a new viewer cannot start while the indicator is absent

### Kill the gateway

With a live stream:

- [ ] terminate the `watchport` process without graceful shutdown
- [ ] indicator detects gateway loss
- [ ] indicator independently deactivates every Watchport-owned Moonlight slot
- [ ] remote video stops
- [ ] restarting the gateway performs stale-slot cleanup before new admission

### Kill the browser/tab

With a live stream:

- [ ] force-close the viewer tab/app
- [ ] browser heartbeat disappears
- [ ] gateway deactivates the Viewer slot after the configured heartbeat timeout
- [ ] host warning disappears when the final viewer is gone

### Suspend/background mobile Safari

- [ ] background Safari long enough for timers/network to suspend
- [ ] the active Viewer capability is reclaimed rather than lingering indefinitely
- [ ] returning to Safari never silently creates a second slot
- [ ] while the Watchport auth session remains valid, the user can deliberately reopen the view
- [ ] after auth expiry, passkey authentication is required again

### Kill both Watchport processes

- [ ] terminate gateway and indicator nearly simultaneously
- [ ] OS service supervision restarts them promptly
- [ ] startup stale-slot cleanup revokes any surviving Viewer capability
- [ ] record the actual worst-case residual viewing interval

This test is important because the data plane lives in Moonlight-Web. The operating-system supervisor is part of the defense against simultaneous control-plane loss.

## G. Revocation and configuration sabotage

- [ ] click normal **Close view** and verify the Moonlight slot becomes Off.
- [ ] click **Lock** while streaming and verify the external slot is revoked before logout succeeds.
- [ ] let the Watchport auth session expire while viewing; external slot must be revoked.
- [ ] deliberately enable Moonlight-Web Internet Access, then attempt a new view.
- [ ] Watchport must reject `local_only=false` and clean up the attempted activation.
- [ ] deliberately alter the slot permission to keyboard/mouse, then attempt a new Watchport activation.
- [ ] Watchport must restore/verify Viewer-only state or refuse admission.
- [ ] occupy every dedicated player slot; Watchport must fail cleanly rather than borrow an owner/full-control slot.

## H. Restart/recovery

- [ ] leave a Watchport-owned Moonlight share active, then restart Watchport.
- [ ] startup cleanup deactivates all configured player slots before admission.
- [ ] restart Moonlight-Web while Watchport is idle; `watchport-doctor` recovers after it returns.
- [ ] restart Moonlight-Web during a view; Watchport/indicator does not report a healthy active view after the stream is gone.
- [ ] restart Tailscale during a view; capability eventually dies or reconnects only under the existing authorized session, never as an uncontrolled duplicate.

## I. Privacy/audit

Inspect `~/.watchport/audit.jsonl` (or configured data directory):

- [ ] useful security lifecycle events are present.
- [ ] no screenshots/video are written.
- [ ] no window titles are recorded.
- [ ] no keystrokes/clipboard data are recorded.
- [ ] no passkey private material is present.
- [ ] no WebAuthn challenge/session token/CSRF token is logged.
- [ ] no Moonlight PIN, `mw_session`, or `mw_player` cookie is logged.

Inspect `watchport.sqlite3`:

- [ ] only public passkey credential material/sign counters and metadata are stored.

## J. Latency and stability

Test at least:

1. client and host on the same LAN but communicating through Tailscale
2. client on cellular / host at home
3. another normal remote network

For each, record:

- [ ] Tailscale path: direct or DERP
- [ ] WebRTC candidate/path if available
- [ ] resolution/FPS/bitrate
- [ ] time from **Open desktop** to first useful frame
- [ ] approximate glass-to-glass latency
- [ ] packet loss/jitter symptoms
- [ ] reconnect behavior after Wi-Fi/cellular transition

Target outcome is not a synthetic benchmark number; the desktop should feel effectively live for observation and text should remain readable. Optimize only after the security tests pass.

## K. Client matrix

At minimum:

- [ ] current iPhone Safari
- [ ] current desktop Chrome/Chromium
- [ ] another desktop browser if it will actually be used

Optional:

- [ ] iPad Safari
- [ ] Android Chrome

## Final gate

Call the host ready only if:

- every mandatory security/failure test passes,
- any skipped test is explicitly justified,
- there is no public ingress,
- View-only is proven below the UI layer,
- host indication and both revocation directions have been physically observed,
- and the remaining risks are understood and accepted.
