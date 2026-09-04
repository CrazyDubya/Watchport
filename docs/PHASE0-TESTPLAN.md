# Phase 0 Test Plan — Streaming Substrate

The first implementation task is empirical. Do not build the authentication gateway before confirming that the streaming substrate can satisfy Watchport's browser, latency, and view-only requirements.

## Questions to answer

1. Can Sunshine reliably capture the target desktop with hardware encoding?
2. Which browser-capable Moonlight/WebRTC bridge works best with current iOS Safari?
3. Is view-only enforced in the backend/bridge rather than only in browser UI?
4. Does the path work entirely over Tailscale without public ingress?
5. What reconnect behavior occurs after browser backgrounding, network change, and sleep/wake?
6. What latency and bitrate are observed for UI-centric desktop viewing?

## Required environments

At minimum:

- host desktop + local LAN viewer
- iPhone/iPad Safari over local Wi-Fi
- iPhone Safari over cellular through Tailscale
- desktop Chromium-class browser over Tailscale

## Profiles to test

- 1280x720 @ 30 fps
- 1920x1080 @ 30 fps
- 1920x1080 @ 60 fps
- 2560x1440 @ 30 fps where supported

Record:

- codec
- bitrate
- encode latency if exposed
- decode/render latency if exposed
- approximate glass-to-glass latency
- CPU/GPU utilization
- text readability
- reconnect time

## Negative/input tests

Attempt to cause input through every transport/API exposed by the selected bridge:

- keyboard
- pointer/mouse
- touch
- gamepad
- clipboard if present
- browser console/direct protocol calls

A candidate fails Watchport's requirements if a viewer can regain input merely by modifying client JavaScript or sending a normally valid bridge message.

## Network tests

Confirm:

- no public port forward is necessary
- service can bind only to localhost/Tailscale address as appropriate
- direct Tailscale path works
- DERP-relayed path remains functional at reduced performance if encountered
- Wi-Fi <-> cellular transition fails/reconnects safely

## Browser lifecycle tests

Test:

- refresh
- duplicate tab
- background for 30 seconds
- background for several minutes
- force-close browser
- phone lock/unlock
- host display resolution change
- host sleep/wake where applicable

## Deliverable

Add a short report under `docs/research/` containing:

- exact upstream projects and versions/commits tested
- license of each candidate
- topology
- measurements
- view-only enforcement findings
- recommendation: adopt / reject / investigate further

Only after this report recommends a substrate should implementation advance to the gateway/passkey phase.
