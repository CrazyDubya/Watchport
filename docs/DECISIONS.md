# Architecture Decision Log

Use this file for concise decisions that materially affect Watchport's trust model, interoperability, or deployment.

## ADR-0001 — Watchport is view-only by architecture

**Status:** Accepted

Watchport V1 does not provide remote keyboard, mouse, touch, clipboard, file, shell, microphone, power, or arbitrary command capabilities.

Rationale: the product goal is rapid observation, and excluding control authority substantially reduces attack surface and accidental privilege growth.

## ADR-0002 — Tailscale is perimeter, not authentication

**Status:** Accepted

Tailscale provides private reachability and device/identity policy. Watchport independently requires WebAuthn/passkey authentication before stream admission.

## ADR-0003 — Reuse mature streaming components

**Status:** Accepted in principle; substrate selection pending validation

Do not implement screen capture, video codecs, hardware encode, or congestion control from scratch. Sunshine is the initial capture/encode candidate. A browser-capable Moonlight/WebRTC bridge must be experimentally validated before becoming a hard dependency.

## ADR-0004 — Host indicator is part of authorization

**Status:** Accepted

The viewing indicator is a security control, not informational decoration. A healthy indicator is required to admit a viewer. Loss of indicator liveness causes stream teardown after a bounded grace period.

## ADR-0005 — Original Watchport code is MIT

**Status:** Accepted

Original Watchport code is MIT licensed. Strong-copyleft dependencies should remain clearly separated runtime components unless there is an explicit reason to create or distribute a derivative work under compatible terms.
