# Build status — 2026-09-10

**0.3.0.dev1: integration preparation; target-system acceptance pending.** This branch improves the security/control plane and prepares the four Mac milestones. It does not contain a verified Mac/iPhone streaming deployment or measured latency results.

**Mac preflight, 2026-09-10 local date:** macOS 26.3.1 arm64, Python 3.12.7/Tk 8.6.14 and Tailscale 1.102.3 inspected. Final automated checks pass (59 Python, 5 browser). Live acceptance remains **blocked**: the official Moonlight-Web v0.2.4 package predates the required activation contract, fails macOS package signature assessment, and has no verified private listener/ingress. No streaming services or routes were started. All 19 live cases and all three network measurement sets remain blocked; recorder exit 1 is expected. See [sanitized Mac evidence](research/MAC-ACCEPTANCE-2026-09-10.md).

## Implemented

- Passkeys with required user verification, one-use first-key bootstrap, session expiry, CSRF, secure cookies, and metadata-only audit logging.
- Ephemeral backend Viewer grants with local PIN redemption, explicit Internet Access configuration checks, input-permission verification, and verified `slot/state=off` revocation responses.
- Admission/probe also require explicitly disabled UPnP. Missing `local_only` on older upstream activations is diagnosed as incompatible and fails closed. Router mappings still require independent verification.
- Every configured slot must revoke successfully. Partial cleanup or failed admission with uncertain revocation blocks new viewing; the gateway retries cleanup. Failed startup cleanup explicitly signals a visible warning even when the restarted gateway has no viewer records.
- The GUI acknowledges a fresh warning revision before capability release. A frozen GUI stops indicator heartbeats. Gateway and indicator independently revoke dedicated player slots and serialize owner operations across processes.
- Phone shell with deliberate reopening after background, stale-admission rejection, revocation before reconnect, bounded foreground network retries, safe-area layout, and fullscreen fallback.
- Private config generation/loading, Mac LaunchAgent generation/install/status/safe removal, and an acceptance recorder that refuses readiness without security evidence and latency samples.

## Four remaining milestones

| Milestone | Prepared in code | Required target evidence / blocker |
| --- | --- | --- |
| Streaming + Tailscale | Adapter, private configuration checks, doctor, source contract | Real Sunshine/Moonlight capture; player-only ingress; correct Desktop identity; no public/LAN bypass |
| Security acceptance | Revocation and warning fixes, regression tests, evidence recorder | Real passkey prompts, backend input rejection, process/GUI failure, replay, lock/sleep/logout |
| Phone UX + latency | Safe lifecycle controls, touch layout, honest authorization timing | Safari and home-screen visual tests, player Join/quality integration, first-frame and glass-to-glass measurements |
| Supervision + recovery | Independent user LaunchAgents, private config, safe cleanup on uninstall | Both-process death and logout behavior, install/upgrade/recovery, Tk compatibility and log growth |

Run [MAC-AGENT-HANDOFF.md](MAC-AGENT-HANDOFF.md) in order. [PLAYER-INGRESS.md](PLAYER-INGRESS.md) is a hard integration gate: reverse-proxying Moonlight's full localhost server could expose owner APIs.

Assigned ports are Watchport HTTPS 8443 → loopback 8787 and player HTTPS 9443 → reserved loopback proxy 8788. Existing routes on 443/10000 are preserved. Different ports do not isolate host-scoped cookies from co-hosted services; the existing unrelated Funnel surface requires review or a dedicated service/device hostname before enrollment. This allocation is not a deployed or accepted topology.

## Threats to the design goals

- The upstream activation API can use an existing owner stream instead of the requested host/app and does not echo the selected identity. A dedicated instance is a temporary operating constraint, not proof of the intended Desktop.
- A `local_only` URL alone does not prove Internet Access is disabled. The adapter now checks the actual setting before new activation. Continuous detection of an administrator changing that setting during a stream is not implemented.
- Killing both Watchport processes removes both revokers. LaunchAgent restart is prepared but unproven; Moonlight's one-hour minimum capability TTL is longer than Watchport's fifteen-minute authentication session.
- User LaunchAgents end at logout. An upstream process that survives logout can outlive Watchport's warning/revokers. Host-lock/sleep behavior and a safe logout solution must be proven before readiness.
- A Tk render acknowledgment proves event-loop progress and a mapped window, not physical visibility above every macOS Space/fullscreen/lock screen. Real observation is mandatory.
- The player may still require a second Join tap. Authorization timing is not first-frame latency, and outer quality/FPS controls have no verified upstream contract.

## Verification

See [the implementation verification record](research/IMPLEMENTATION-VERIFICATION-2026-09-10.md) for local automated results, environment constraints, and checks that remain unperformed. The live report must record the tested commit and exact component/device versions.
