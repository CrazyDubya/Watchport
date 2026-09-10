# Immediate next actions

Continue with [MAC-AGENT-HANDOFF.md](MAC-AGENT-HANDOFF.md) on the target Mac. The gateway, passkeys, lifecycle adapter and indicator exist; do not restart the old bootstrap plan.

1. Install/pair the versioned Sunshine + Moonlight-Web stack and prove a narrow, Tailscale-only player ingress. Preserve the intended Desktop identity; do not expose localhost management via a generic proxy.
2. Complete the real-device security matrix with evidence, including partial revocation, GUI stall, process kills, replay and host logout.
3. Finish the Safari player interaction and measure first-frame, glass-to-glass and reconnect latency on LAN, cellular and remote Tailscale paths.
4. Validate the prepared Mac LaunchAgents, simultaneous failure, safe upgrade/uninstall and passkey recovery. Publish sanitized results and update BUILD_STATUS.

`watchport-acceptance summary` must remain incomplete until every required security case and latency sample is recorded. No remote input, public relay, OS unlock or broad tailnet policy is authorized by this plan.
