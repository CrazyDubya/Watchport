# Watchport: Mac agent execution handoff

The project owner has authorized repository changes and working through the four milestones. Continue on the target Mac with this branch, preserving local changes. Read AGENTS.md first. This is a view-only stream; remote input and OS unlock are outside this work.

The Linux-side implementation is prepared. **No real Mac or iPhone acceptance has been performed here.** Return evidence rather than marking implementation as live acceptance. Do not publish credentials or raw environment/network dumps to this public repository.

## 1. Validate the real streaming stack and private routing

1. Fetch `codex/mac-integration-readiness` from CrazyDubya/Watchport into an isolated worktree. Record its commit. Inspect installed Tailscale, Sunshine and Moonlight-Web versions before installing anything.
2. Use Python 3.12+ with matching Tk support (`python3.12 -m tkinter` must display a window in the logged-in GUI session). Create a venv and install `-e '.[dev]'`. Run `pytest` and `node --test tests/browser/viewer.test.cjs`.
3. Use the upstream **linckosz/moonlight-web** API, not a similarly named bridge. Read `research/UPSTREAM-CONTRACT.md`. Start with separately installed Sunshine and a dedicated Moonlight-Web instance; do not silently switch to its newer native capture engine. Record exact upstream commit, binary version, licenses and architecture. Use official install paths and normal macOS permission dialogs; do not disable Gatekeeper or SIP.
4. Locally pair the intended Sunshine host and its **Desktop** app. Verify hardware capture/encode. Keep Internet Access disabled, UPnP disabled, and unused remote administration disabled. Check existing mappings rather than assuming that disabling UPnP removed old mappings.
5. Obtain the actual MagicDNS hostname from the host's Tailscale status. Initialize private config once:

   ```sh
   .venv/bin/python -m watchport.host init --hostname ACTUAL-DEVICE.ACTUAL-TAILNET.ts.net
   ```

   Edit `~/.watchport/config.env` locally (0600). Check actual Moonlight HTTPS port, then set host UUID and Desktop app ID using `.venv/bin/python -m watchport.doctor`. The generated gateway uses local port 8787; public-to-the-tailnet Watchport HTTPS uses 8443. This avoids Moonlight's common 8443 fallback conflict. All commands load this config automatically.
6. Run gateway and indicator in the GUI login session. Publish only the gateway while bootstrapping, after inspecting existing Serve configuration:

   ```sh
   tailscale serve status
   tailscale serve --bg --https=8443 http://127.0.0.1:8787
   ```

   Preserve unrelated Serve routes and tailnet policy. Never use Funnel or an unrestricted policy.
7. **Do not expose the complete Moonlight localhost server through a generic reverse proxy.** Its localhost trust can turn remote requests into management requests. Complete a player-only ingress for the exact installed version, or prove a direct tailnet listener preserves remote-peer identity and blocks management. Read `PLAYER-INGRESS.md`; add a reviewed implementation/configuration and negative tests to the branch. Keep direct media behind tailnet policy as well.
8. From another allowed tailnet device, verify management isolation, then verify Watchport/player/media are unreachable from a denied device and with Tailscale disconnected. Check direct versus DERP routing and actual WebRTC candidates. Do not record raw addresses/credentials in a public report.

**Exit:** intended Desktop in Safari over tailnet only, real backend no-input enforcement, verified player ingress, versioned topology report. If an upstream API or capture requirement fails, record the exact sanitized failure and implement the smallest correction in a separate commit. Do not loosen a security gate to obtain a demo.

## 2. Prove passkeys, warning and failure behavior

1. Create a fresh evidence file outside git:

   ```sh
   .venv/bin/python -m watchport.acceptance --report .acceptance/mac.json init \
     --sunshine ACTUAL_VERSION --moonlight-commit ACTUAL_COMMIT \
     --tailscale ACTUAL_VERSION --iphone 'ACTUAL iOS / Safari version' \
     --desktop 'ACTUAL desktop browser/version'
   ```

2. Run `watchport-bootstrap` on the host, enroll on the **real tailnet HTTPS hostname** on the iPhone, and complete Face ID/security-key verification with the project owner. Token entry and platform prompts require the person/device; an agent cannot substitute for a physical authentication result.
3. Execute every mandatory item in `LIVE-ACCEPTANCE.md`, including GUI-thread stall independently of process death. The gateway now requires acknowledgment of the displayed warning revision before minting a player capability. A stale revision, frozen GUI or missing indicator must not grant access.
4. Kill the gateway, indicator, browser, and both Watchport processes separately. Physically observe video stopping; an HTTP 200 is not a video test. Try old cookies/URLs afterwards. Test one failed upstream revocation while others succeed; unresolved slots must remain unsafe and new admission must stay blocked.
5. Test phone lock/background, duplicate tabs, host lock, sleep/wake and logout. The Watchport **Lock** button revokes viewing and logs out of Watchport; it does not lock or unlock macOS. Until native host-lock handling is proven, do not claim device-lock binding or readiness while the GUI login session is absent.
6. Record each result, not merely a checked box:

   ```sh
   .venv/bin/python -m watchport.acceptance --report .acceptance/mac.json check indicator_kill \
     --status pass --evidence 'Actual observation, elapsed seconds, and replay result'
   ```

**Exit:** all security cases have real evidence. Failed/blocked/not-run cases remain blockers.

## 3. Measure and finish the phone experience

The browser shell now pauses on background, drops late admissions, requires deliberate reopening after phone backgrounding, offers bounded retries only for network failures while foregrounded, and requests revocation before reconnecting. It includes fullscreen fallback, safe-area layout and a home-screen manifest. No offline worker caches authentication or video.

Quality remains the upstream player's **720/1080/1440** selection. Do not add shell controls that pretend to apply unsupported FPS/bitrate settings. The embedded player may need its own Join tap: automatic one-tap streaming and verified first-frame telemetry remain an upstream integration task. Record these extra taps and any Safari iframe/autoplay/standalone restrictions.

Measure at least five samples each on LAN-through-Tailscale, cellular and another remote network. Record actual codec/resolution/FPS/bitrate, direct/DERP path, readability, first useful frame, glass-to-glass latency, and reconnect time. The displayed **Access granted** timing measures authorization only; iframe load also does not measure a decoded frame. Use a changing host stopwatch and an external camera showing both displays to measure glass-to-glass delay without assuming synchronized clocks. Keep recordings private; commit only sanitized numbers.

```sh
.venv/bin/python -m watchport.acceptance --report .acceptance/mac.json measure \
  --network lan --path direct --profile 'ACTUAL codec/resolution/FPS/bitrate' \
  --first-frame-ms ACTUAL_MS --glass-to-glass-ms ACTUAL_MS \
  --reconnect-ms ACTUAL_MS --readable yes
```

Initial engineering targets in the report: p95 first frame ≤2500 ms; glass-to-glass ≤150 ms LAN and ≤300 ms remote; reconnect ≤5000 ms. These are targets, not achieved measurements. Any target change needs a recorded reason. Tune after the security tests pass; do not enable a public fallback for speed.

## 4. Supervise, package and validate recovery

Use `MAC-OPERATIONS.md`. Generate/review the plists first; installation runs the gateway and indicator as independent user LaunchAgents in the Aqua login session, without root. Perform supervision acceptance with a deliberately safe test desktop before daily use. Startup cleanup must succeed for every dedicated player slot before admission.

Verify clean install, restart, safe uninstall, upgrade, preserved credentials, simultaneous failure, and log growth. A loaded launchd job is not proof of a healthy process or visible warning. Login-scoped agents are not a guarantee after logout; if Sunshine/Moonlight persists, add a proven revocation/supervision solution before accepting that case.

Finish with:

```sh
.venv/bin/python -m watchport.acceptance --report .acceptance/mac.json summary
```

Nonzero means incomplete/failed acceptance, not a broken recorder. Publish a sanitized `docs/research/MAC-ACCEPTANCE-YYYY-MM-DD.md` containing exact versions, Watchport commit, topology/port roles, test evidence, latency medians/p95, blockers and next actions. Update BUILD_STATUS and the PR with those findings. Never commit `.acceptance`, config.env, passkey databases, cookies, PINs, screen recordings or raw host logs.
