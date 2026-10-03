# Stream adapter contract and remaining validation

The former static Viewer URL handoff has been replaced by `MoonlightWebAdapter.open`, `close`, `cleanup_stale_slots`, `revoke_all`, `probe` and `apps_for`. Watchport owns only configured player slots 2–4. `StreamGrant` contains the scoped player cookie and viewer URL; owner credentials stay local.

Implemented contract:

- Viewer input flags must be false before a capability is released.
- Internet Access must be explicitly disabled; a local link is an additional check.
- Admission requires a fresh GUI acknowledgment before minting and rechecks authorization afterwards.
- Revocation requires the requested slot to be reported `off`; any failed slot blocks admission and remains tracked as uncertain.
- Gateway and indicator use a bounded cross-process lock for owner/PIN operations. Host kill, watchdog and startup cleanup cover uncertain capabilities.

Remaining live proof: physical video teardown and old-cookie rejection after every failure, strict intended-host/app verification, private player ingress, and simultaneous-process/logout handling. A successful upstream response is not evidence that the remote display stopped.

See [UPSTREAM-CONTRACT.md](research/UPSTREAM-CONTRACT.md), [PLAYER-INGRESS.md](PLAYER-INGRESS.md) and [MAC-AGENT-HANDOFF.md](MAC-AGENT-HANDOFF.md).
