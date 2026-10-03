# Mac operations

Use an installed Python 3.12+ with working Tk and a stable repository/venv location. Do not move the venv while services use it. Commands below run from the Watchport checkout; the default private config is `~/.watchport/config.env`, mode 0600. Environment variables override file values. Config is parsed as data, never sourced as shell code.

## Preview, then install

After real stack setup and an ordinary foreground smoke test:

```sh
.venv/bin/python -m watchport.host install --dry-run --output /tmp/watchport-launch-preview
plutil -lint /tmp/watchport-launch-preview/net.watchport.gateway.plist
plutil -lint /tmp/watchport-launch-preview/net.watchport.indicator.plist
.venv/bin/python -m watchport.host install
.venv/bin/python -m watchport.host status
```

The two agents use `gui/<uid>`, Aqua session scope, RunAtLoad and KeepAlive. Paths with spaces are represented as plist argument arrays. Plists contain only the private config path, not its secrets. Installation checks Tk import, configured host/app and Moonlight's private mode; it does not prove the remote stream works. Inspect the host warning and run the live acceptance suite. KeepAlive restarts may be throttled; measure actual timing.

The installer refuses to overwrite existing Watchport plists. It does not install Sunshine/Tailscale/Moonlight, change screen permissions, modify global firewall policy, or publish a service.

## Stop, upgrade or remove

```sh
.venv/bin/python -m watchport.host uninstall
```

This stops new gateway admissions, confirms every dedicated Moonlight slot is Off, then unloads the indicator. Failed revocation keeps the indicator available and aborts removal. Credentials/configuration remain on disk. If Moonlight is unavailable, restore its control API and retry; physically stop its stream/worker if required before maintenance. Do not erase the warning to conceal an unresolved stream.

For an upgrade: use the old environment to uninstall safely; update the checkout; install dependencies; run tests; reinstall the two agents together. The render-acknowledgment protocol changed in 0.3.0.dev1: an old indicator cannot admit viewers. Never run old/new control processes together.

## Recovery

- Missing/rejected passkey: first use another already enrolled authenticator if available. This UI currently exposes first enrollment only; an additional-key/recovery UI is still pending. Do not enable open remote registration.
- Total credential loss: uninstall/revoke first, remove the gateway Serve route using its exact original flags, and keep service private. Preserve an encrypted backup of the old database/config before an explicit local reset. A new empty credential store requires a new host bootstrap ceremony and invalidates the old credential set. This destructive reset is intentionally not automated.
- Crash: inspect local gateway/indicator logs and `watchport-doctor`; restore upstream availability. The gateway retries unresolved stale-slot cleanup, blocking admission until all owned slots are confirmed Off.
- Logout/reboot: user agents exist only with their GUI login session. Test the real Moonlight/Sunshine lifecycle; do not treat LaunchAgents as proof that a stream stops after logout or simultaneous control loss.
- Logs: local files may grow. After safe stop, rotate/archive them locally before restart. Do not attach raw logs or config to public issues.

References: [Apple launchd agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html), [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve), [Sunshine macOS setup](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html).
