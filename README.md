# Watchport

**A secure, low-latency, view-only window into your own desktop.**

Watchport is a small self-hosted system for opening a browser on a trusted device, authenticating with a passkey, and immediately viewing a live stream of a desktop over Tailscale.

It is deliberately **not** a remote-control product.

## Product principles

1. **View-only is structural, not cosmetic.** A viewer must not gain keyboard, mouse, touch, clipboard, file-transfer, shell, microphone, or other control capabilities simply because a front-end control is hidden.
2. **Tailscale is the network perimeter.** The service should not require public ports, a public relay, or an Internet-facing application endpoint.
3. **Passkeys are the application gate.** Possession of a tailnet-connected device is not, by itself, authorization to view the desktop.
4. **Viewing must be visible at the host.** Every active viewer produces a persistent host-side indication for the entire session.
5. **Fail closed.** If authentication, authorization, or the host indicator heartbeat fails, the stream terminates.
6. **Keep the trusted computing base small.** Reuse mature capture/encoding/networking components rather than rebuilding them.
7. **Control, if ever added, is a separate product surface.** Do not quietly grow the viewer into remote desktop.

## Intended architecture

```text
Browser
  |
  | Tailscale-only HTTPS
  v
Watchport Gateway
  |- WebAuthn/passkey authentication
  |- short-lived session authorization
  |- viewer lifecycle + audit events
  |- stream admission policy
  |
  +----> browser streaming bridge / viewer
                 |
                 v
              Sunshine
                 |
                 v
              Desktop

Host Indicator <---- local viewer heartbeat ---- Gateway
```

The initial implementation should investigate **Sunshine + a browser-capable Moonlight/WebRTC bridge** as the streaming substrate rather than implementing desktop capture or codecs ourselves.

## Non-goals for v1

- keyboard or mouse control
- touch injection
- clipboard sync
- file transfer
- remote shell
- microphone upstream
- arbitrary application launch
- reboot/shutdown/wake controls
- login-screen manipulation
- public Internet exposure
- cloud account requirement

Audio playback is optional and should default off until explicitly implemented and threat-modeled.

## Target UX

After initial enrollment:

1. Open a bookmarked Watchport URL on a tailnet-connected phone/laptop.
2. Authenticate with Face ID / Touch ID / platform passkey.
3. Stream starts quickly.
4. Host desktop shows a persistent **DESKTOP IS BEING VIEWED** indicator until the final viewer disconnects.
5. Backgrounding/foregrounding the browser should reconnect safely without weakening authentication policy.

## Default quality targets

Start with conservative UI-centric profiles:

- Crisp: 2560x1440 @ 30 fps
- Balanced: 1920x1080 @ 30 fps
- Live: 1920x1080 @ 60 fps
- Low Data: 1280x720 @ 20-30 fps

Prefer text clarity over unnecessary frame rate for ordinary desktop observation.

## Security invariants

A conforming Watchport implementation must preserve all of these:

> The stream cannot be reached outside the configured private network perimeter.
>
> Network authorization alone cannot start viewing.
>
> Viewing grants no input/control capability.
>
> Every active viewer produces a persistent host-side indicator.
>
> The stream dies if authorization or the indicator heartbeat disappears.

See [docs/SECURITY.md](docs/SECURITY.md).

## Agentic development

This repository is intended to be safely advanced by coding agents. Read [AGENTS.md](AGENTS.md) before modifying the implementation.

Agents should prefer small, independently testable components and must not weaken a security invariant merely to make a demo work.

## Licensing

Watchport's own original code is intended to use the MIT License. External components retain their own licenses.

Sunshine is GPL-3.0 licensed, and browser/Moonlight implementations may also be GPL-licensed. Watchport should initially integrate with such software as separately installed/runtime components rather than copying or vendoring their code into this repository. See [docs/LICENSING.md](docs/LICENSING.md).

## Status

**Design / bootstrap.** The architecture is intentionally specific, but implementation choices should be validated experimentally before being frozen.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).
