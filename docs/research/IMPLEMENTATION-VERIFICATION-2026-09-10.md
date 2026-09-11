# Implementation verification — 2026-09-10

Scope: original Watchport changes on `codex/mac-integration-readiness`, based on main `344f5b50a5cc4b7d5acfe465fad2b4d161dd34b8`. The branch commit identifies the exact reviewed files. This Linux environment has no attached Mac, iPhone, Sunshine stream or Tailscale deployment.

## Passed locally

- 48 Python tests on Python 3.12, including partial revocation, malformed slot state, Internet Access configuration, stale GUI revision, admission expiry after minting, orphan cleanup through host kill, startup uncertainty without viewer records, private config, origin separation, cross-process control locking and acceptance gating.
- 5 Node browser-lifecycle tests: late admission after background, deliberate foreground reopen, no authorization retry, manual reconnect blocked by uncertain revocation, and revocation before network retry. These use a simulated browser environment, not Safari or a video decoder.
- Python compile, JavaScript syntax and `git diff --check`.
- Editable package build/install as 0.3.0.dev1 without adding runtime dependencies.
- CLI smoke: private config initialization, non-overwriting plist preview with the venv interpreter preserved, and an incomplete acceptance report returning exit 1. No Mac service was started.

## Environment constraints

The first dependency resolution selected cryptography 50.0.1, whose native wheel raised a BUS ERROR during import in this container before tests could run. Local verification used cryptography 46.0.5 and pyOpenSSL 26.0.0 with webauthn 2.8.0. This workaround is confined to the local virtual environment; repository requirements were not pinned or loosened. Fresh GitHub CI and the target Mac installation must validate their actual dependency sets. Two upstream deprecation warnings remain from Starlette/httpx and anyio.

Browser visual verification was attempted through agent-browser, but its daemon failed to start. Installing Playwright Chromium then failed because browser downloads returned network/CDN errors. No screenshot, rendered phone layout, Safari behavior or first decoded frame is claimed as verified.

## Pending evidence

The four milestones in [MAC-AGENT-HANDOFF.md](../MAC-AGENT-HANDOFF.md) still require target execution: player-only ingress, capture/encode and Desktop identity, real passkey ceremonies, physical warning/teardown, latency and readability, and launchd/simultaneous-failure/logout/recovery behavior. CI and simulated tests cannot replace these observations. No latency or readiness result has been fabricated.
