# Mac acceptance evidence — 2026-09-10

**BLOCKED — preflight completed; no live Mac/iPhone streaming acceptance.** Date is America/New_York (report creation on 2026-09-11 UTC). No service was published, no capture began, and no passkey was enrolled. All 19 mandatory live cases remain blocked. The private acceptance summary exits **1**, with `ready=false`, 25 blockers and no network measurements. That exit is expected.

## Provenance and environment

The requested branch was cloned at `f41bf0dfc94e0d07a0be73cbf715e051d45e2653` and checked out in an isolated worktree. During preflight, the remote advanced to `ec13df888fa0075ae592f459d8b8649390146045` with the owner's 9443 allocation. Local work was preserved, that update was fast-forwarded, and overlapping changes were reconciled without rewriting history.

Tested code commit: **`f1584c41b1006ea27909bc642af77e99affdbb78`**, including port-validation commit `11e77f6d5228a4878ded0c522108b6c95f50dad3`. This evidence and BUILD_STATUS update are documentation-only changes after that code commit.

| Component | Observed version / state |
| --- | --- |
| Host | macOS 26.3.1 (a), build 25D771280a, arm64; console owned by the invoking user |
| Python | python.org framework 3.12.7; dedicated Python 3.12 venv, editable `.[dev]` install succeeded |
| Tk | 8.6.14; actual test window reported mapped=true and viewable=true in its event loop |
| Tailscale | 1.102.3; client commit `9329c3677031109ff6d0b80abee0cddc8f35ff6f`; backend Running, local device online, MagicDNS present |
| Desktop browsers | Safari 26.3.1 and Chrome 152.0.7977.83 installed; real authentication/playback untested |
| iPhone / iOS / Safari | Unknown; no physical device result available |
| Node | v25.6.1 |
| Main Python packages | FastAPI 0.141.1, Starlette 1.6.0, Pydantic 2.13.5, Uvicorn 0.52.4, WebAuthn 2.8.0, pytest 9.1.1, httpx 0.28.1 |
| Sunshine runtime | Not found in standard executable/app locations; not installed or launched by this run |
| Moonlight-Web runtime | Not found in standard executable/app/config locations; not installed or launched by this run |

`python3.12 -m tkinter` ran in the GUI session and was stopped after preflight. A separate short-lived real Tk program measured mapping/viewability. The GUI inspection tool could enumerate Python but did not return a usable window inspection, so neither this nor an import proves physical warning visibility. No screenshot/video evidence was captured or committed.

## Downloaded candidates, not installed versions

Both packages came from official upstream GitHub releases. They were inspected locally, not redistributed or executed. Downloaded packages and source inspection files remain outside tracked content. Watchport still uses process/network integration; no GPL code was copied into its MIT components.

| Candidate | Exact source / architecture | Local package assessment |
| --- | --- | --- |
| Sunshine `2026.906.222525` | Release commit `cb72dffa3233c5815cd5ba88f09f049dd679ba75`; advertised macOS arm64 asset; GPL-3.0 family | Mounted read-only; bundle version matches; `spctl --assess --type execute` accepted, `source=Notarized Developer ID`; image subsequently ejected |
| Moonlight-Web `0.2.4` | Tag commit `b7e1f66fc2dc68d412ec8ae8a256fce26e4aedf5`; expanded binary is Mach-O arm64; GPL-3.0-or-later source notices | `pkgutil --check-signature`: no signature, exit 1. `spctl --assess --type install`: rejected, `source=no usable signature`, exit 3. Package expanded for inspection only |

SHA-256 of downloaded assets:

- `Sunshine-macOS-arm64.dmg`: `b630d35a184d8eaff39c5104f3c6a0c40e91ddc447ccf7a0c5b24706465fab6a`
- `moonlightweb-0.2.4-macos-arm64.pkg`: `e96fba073475ca956a52e6f38ccd67564993c5f814cb74ec3eddaf3f9254887c`

Sources: [Sunshine release](https://github.com/LizardByte/Sunshine/releases/tag/v2026.906.222525), [Moonlight-Web release](https://github.com/linckosz/moonlight-web/releases/tag/v0.2.4). Hashes establish which downloads were inspected; they do not establish runtime acceptance.

The v0.2.4 activation route ignores requested host/app/TTL and omits `local_only`. Its HTTP/HTTPS server binds all interfaces, UPnP defaults on, and its installer adds a broad application-firewall allowance and launches services. This candidate cannot satisfy the handoff as shipped. The newer contract inspected at `ff98a358a6bb53340d2b33b4bdf0f7a72311a12d` is a different revision. See [versioned source evidence](UPSTREAM-CONTRACT.md#mac-package-inspection--2026-09-10-local-date). No Gatekeeper/SIP bypass or upstream capture-engine switch was used.

## Ordered handoff execution

| Handoff step | Result and remaining gate |
| --- | --- |
| 1.1 — checkout/inventory | Done; base commit and remote advancement above. No open Watchport issues returned; existing PR #4 inspected. Installation inventory preceded downloads |
| 1.2 — Python/Tk/tests | Fresh venv installed; baseline 48 Python / 5 browser tests passed. Tk mapping measured; physical GUI visibility remains unverified |
| 1.3 — upstream adoption | BLOCKED on the incompatible, unsigned v0.2.4 package and lack of a proven private listener/media topology |
| 1.4 — Sunshine/Desktop | BLOCKED; no pairing, hardware capture/encoding, permission ceremony, owner-stream override test or router-mapping inspection |
| 1.5 — local config/doctor | Private config initialized once from actual MagicDNS, mode 0600, assigned origins 8443/9443. Host UUID/app ID remain unset. Doctor exit 3: config OK, Moonlight control unavailable (TLS timeout at generated loopback control default). No actual control port or healthy upstream asserted |
| 1.6 — gateway/indicator/Serve | BLOCKED by earlier gates. Existing Serve routes inspected; no gateway/indicator or Serve publication started |
| 1.7–1.8 — ingress/perimeter | BLOCKED. No proxy for an unadopted version was deployed; no allowed/denied-device, disconnected-Tailscale, ICE or direct/DERP stream test |
| 2 — security | Private recorder initialized and every case given an individual blocked reason below. No token generation, enrollment, physical failure injection or video/replay test |
| 3 — phone/latency | BLOCKED behind security; no synthetic timings substituted for decoded frames or camera measurements |
| 4 — supervision/recovery | Independent preparation only: generated two plists under the private evidence directory; both pass `plutil -lint`. Host status shows both jobs unloaded. No install, restart, uninstall, upgrade, logout/reboot or credential recovery test |

Dependent live steps were evaluated in order and left blocked. Config generation and plist previews are preparation, not milestone exits. Private config, acceptance JSON and source/packages remain local; no raw host/network dump is part of this report.

## Assigned topology and unresolved perimeter

| Role | Port / target | State |
| --- | --- | --- |
| Watchport HTTPS | tailnet TCP 8443 → loopback 8787 | Assigned, not published |
| Player HTTPS | tailnet TCP 9443 → loopback 8788 | Assigned, proxy not implemented/deployed |
| Existing unrelated services | TCP 443 and 10000 | Existing routes preserved; existing Funnel configuration observed |
| Moonlight management | Actual loopback HTTPS port unknown | Unconfigured runtime; generated control default is not proof of a listener |
| Direct WebRTC/Sunshine media | Unknown | Must verify actual ports/candidates and restrict authorized peers before use |

Local TCP probes found no accepting loopback listener on 8787, 8788, 8443 or 9443. This says nothing about denied-device/public reachability and does not pass perimeter acceptance. Tailnet policy, existing Serve/Funnel configuration, firewall settings and router mappings were not modified. Intended clients need narrow TCP 8443/9443 grants; media access must wait for verified ports.

The port change resolves allocation overlap only. Cookies cross ports on one hostname; the unrelated services, especially the existing Funnel surface, must be reviewed for cookie exposure/overwriting or Watchport needs a dedicated Tailscale service/device identity. No enrollment or publication should precede that review. See [PLAYER-INGRESS](../PLAYER-INGRESS.md).

## Fixes and automated evidence

- `host init --player-port` validates a nonprivileged HTTPS player port distinct from gateway HTTPS 8443 before writing any config. Default stays 9443; existing config is not overwritten. Tests cover invalid/shared ports and an alternate allocation.
- Probe/admission now require both Internet Access and UPnP to be explicitly false JSON booleans. True, missing, null, numeric and string UPnP values block authority creation. A v0.2.4-shaped response without `local_only` is rejected, cleaned up and never redeemed; its diagnostic identifies the incompatible contract.
- No new dependency or manifest constraint change. These checks do not inspect old router mappings or continuously detect upstream settings changes during streaming.

Final validation at the tested code commit:

| Check | Result |
| --- | --- |
| Targeted host/config/adapter tests | 36 passed |
| Full Python suite | **59 passed**, 2 upstream deprecation warnings, 1.74 seconds |
| Browser lifecycle suite | **5 passed** |
| `pip check` | No broken requirements |
| LaunchAgent plist syntax | Both OK; previews only |
| `git diff --check` | Clean before commits |
| Live acceptance summary | **exit 1, ready=false, 25 blockers**, expected |

Final Python tests used an empty private test config via `WATCHPORT_CONFIG_FILE` so the freshly created host config was not consumed by tests. The two warnings concern Starlette's httpx test client and AnyIO portal alias; no dependency was changed to suppress them. The earlier local 60-test run preceded remote reconciliation; a duplicate default-port test was removed after incorporating equivalent upstream coverage.

## Mandatory live cases

| Case | Status | Evidence / blocker |
| --- | --- | --- |
| `private_perimeter` | BLOCKED | Blocked at milestone 1: no compatible streaming service or verified player ingress; denied-device, Tailscale-disconnected, router mapping and media-port tests not run. Existing unrelated Serve/Funnel routes preserved. |
| `management_isolation` | BLOCKED | Blocked: v0.2.4 source binds HTTP/HTTPS on all interfaces; no reviewed player-only ingress or alternate-listener isolation deployed. |
| `desktop_identity` | BLOCKED | Blocked: v0.2.4 activation ignores host_uuid/app_id/ttl_secs; no Sunshine pairing, Desktop selection or live wrong-host test. |
| `passkey_iphone` | BLOCKED | Blocked: no final verified private topology or available physical iPhone authentication observation; no enrollment attempted. |
| `passkey_desktop` | BLOCKED | Blocked: no final verified private topology; installed browser versions recorded, no real passkey authentication performed. |
| `bootstrap_replay` | BLOCKED | Blocked for live acceptance: no bootstrap/enrollment ceremony; automated tests do not substitute for real-host replay evidence. |
| `origin_replay` | BLOCKED | Blocked for live acceptance: no real authenticated stream or device session; automated security tests only. |
| `view_only` | BLOCKED | Blocked: no live stream or hostile-input observation on the host; adapter regression tests only. |
| `warning_before_pixels` | BLOCKED | Blocked: Tk 8.6.14 window reports mapped/viewable, but warning-before-first-frame and physical Space/fullscreen visibility unobserved. |
| `indicator_kill` | BLOCKED | Blocked: no live stream; video-stop time and replay after indicator death not observed. |
| `indicator_ui_stall` | BLOCKED | Blocked: no live stream; independent GUI stall, video stop and replay not observed. |
| `gateway_kill` | BLOCKED | Blocked: no live stream; independent revocation and physical video stop unobserved. |
| `both_killed` | BLOCKED | Blocked: live services not installed; residual viewing after simultaneous death unmeasured. |
| `partial_revoke` | BLOCKED | Blocked for live acceptance: synthetic partial-revocation tests pass, but real upstream failure and video behavior unobserved. |
| `session_expiry` | BLOCKED | Blocked: no live view to test expiry, Close view, local Disconnect viewers or Watchport Lock. |
| `phone_lifecycle` | BLOCKED | Blocked: no physical iPhone Safari session; lock, background, duplicate tabs and network changes unobserved. |
| `host_lifecycle` | BLOCKED | Blocked: no safe live test desktop; lock/sleep/logout/reboot acceptance not attempted. |
| `recovery` | BLOCKED | Blocked: dry-run LaunchAgent plists pass plutil; both jobs unloaded. Install/restart/uninstall/upgrade, credential preservation and log growth unverified. |
| `privacy` | BLOCKED | Blocked for runtime acceptance: no real gateway audit/passkey database to inspect. Committed preflight evidence is separately sanitized; no capture was recorded. |

## Measurements

| Network | Samples | First useful frame median / p95 | Glass-to-glass median / p95 | Reconnect median / p95 | Path/profile/readability |
| --- | --- | --- | --- | --- | --- |
| LAN through Tailscale | 0 | N/A | N/A | N/A | Unverified |
| Cellular | 0 | N/A | N/A | N/A | Unverified |
| Other remote network | 0 | N/A | N/A | N/A | Unverified |

Targets remain unchanged: five or more samples per network; p95 first frame ≤2500 ms, glass-to-glass ≤150 ms LAN / ≤300 ms remote, reconnect ≤5000 ms. No quality, codec, FPS, bitrate, first-frame, glass-to-glass or reconnect result was invented.

## Resume in order

1. Obtain a reviewed compatible Moonlight-Web build matching the activation contract, retaining Sunshine as the capture source. Resolve installation/signing through normal macOS controls and establish an explicit private listener plus media restriction plan before starting it. The v0.2.4 installer is not an acceptable shortcut.
2. Install/pair Sunshine separately, select the intended Desktop, and verify capture/encode plus Internet Access/UPnP and existing mappings. Confirm the real control port and complete the local host/app config.
3. Resolve shared-hostname cookie trust, implement the pinned player ingress on 8788, and prove negative management/API/WebSocket and allowed/denied-device tests before exposing 9443. Preserve 443/10000.
4. With the owner and physical iPhone, perform passkeys, all live failure/replay/lock cases, then phone measurements and supervision/recovery. Keep each gate blocked until its required observation exists.
