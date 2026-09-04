# Target-system setup

This is the procedure to use when Watchport moves from pre-integration code to a real desktop. Do not skip the live acceptance checklist afterwards.

## 1. Prerequisites

On the host desktop:

- Tailscale, signed into the intended private tailnet
- Python 3.12+
- Sunshine, installed and working locally
- Moonlight-Web, installed locally and paired with Sunshine
- a desktop/session app in Sunshine that represents the screen Watchport should show

Watchport does not require Docker, a VPS, a public DNS record, router forwarding, Cloudflare Tunnel, or Tailscale Funnel.

## 2. Moonlight-Web safety settings

Before integrating Watchport:

1. Pair Moonlight-Web with Sunshine locally.
2. Confirm ordinary local streaming works.
3. **Disable Moonlight-Web Internet Access / rendezvous sharing.** Watchport rejects any activation that Moonlight reports as `local_only=false`.
4. Do not use Moonlight-Web player slots 2, 3, or 4 for unrelated sharing if Watchport is configured with the default slot set. Those become Watchport-owned safety capabilities.
5. Do not grant Watchport remote-admin credentials. It uses Moonlight-Web's localhost-only rotating admin key plus an ephemeral, one-use PIN flow.

## 3. Install Watchport

```bash
git clone https://github.com/CrazyDubya/Watchport.git
cd Watchport
python3.12 -m venv .venv
```

Activate the environment:

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install --upgrade pip
pip install -e '.[dev]'
pytest
```

Do not continue if the test suite fails.

## 4. Configure the private hostname

Choose the host's MagicDNS name, for example:

`desktop.example-tailnet.ts.net`

Watchport uses the same hostname for two private HTTPS surfaces:

- `https://desktop.example-tailnet.ts.net:8443` — Watchport/passkey gateway
- `https://desktop.example-tailnet.ts.net` — Moonlight-Web player surface

This same-hostname requirement is deliberate: Watchport redeems the Moonlight player PIN locally and sets Moonlight's scoped `mw_player` cookie from the authenticated Watchport response. Cookies are host-scoped rather than port-scoped.

Copy `.env.example` into the service environment and set at minimum:

```text
WATCHPORT_ORIGIN=https://desktop.example-tailnet.ts.net:8443
WATCHPORT_RP_ID=desktop.example-tailnet.ts.net
WATCHPORT_STREAM_ORIGIN=https://desktop.example-tailnet.ts.net
WATCHPORT_INDICATOR_SECRET=<strong random value>
```

Generate the indicator secret locally, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Never commit the populated environment file.

## 5. Keep the Watchport listener on loopback

The gateway intentionally refuses a non-loopback `WATCHPORT_HOST`.

Start it locally:

```bash
watchport
```

Then privately publish it with Tailscale Serve. Current Tailscale CLI supports HTTPS serving of a local target; the exact command should be checked on the installed Tailscale version with `tailscale serve --help` before applying it.

A representative configuration is:

```bash
tailscale serve --bg --https=8443 8443
```

This is **Serve**, not Funnel. Funnel is out of scope because it deliberately makes a service reachable from the public internet.

## 6. Tailscale access policy

Use a dedicated destination tag or host selector for the desktop and grant only the devices/users that should be able to reach Watchport/Moonlight.

Current Tailscale Grants support protocol/port-specific permissions such as `tcp:443`, `tcp:8443`, and `udp:<port>`. During live integration, narrow this to the actual Moonlight-Web/WebRTC ports verified on the host. Do not grant `*` merely for convenience.

The desired end state is conceptually:

```json
{
  "grants": [
    {
      "src": ["<your user/group/device selector>"],
      "dst": ["<Watchport desktop selector>"],
      "ip": ["tcp:443", "tcp:8443", "udp:<verified-webrtc-port>"]
    }
  ]
}
```

Use the actual selectors and verified media port from your tailnet. Treat this as a template, not a paste-ready policy.

## 7. Enroll the first passkey

The first passkey is intentionally **not** enrolled from `localhost`, because WebAuthn origin/RP verification must match the real tailnet HTTPS hostname.

On the host run:

```bash
watchport-bootstrap
```

It prints a one-time bootstrap token. On a trusted tailnet device:

1. Open `https://desktop.example-tailnet.ts.net:8443`.
2. Paste the bootstrap token.
3. Choose **Enroll first passkey**.
4. Complete Face ID / Touch ID / Windows Hello / security-key verification.

After successful registration the bootstrap token is deleted and cannot be reused.

Additional passkeys require an already authenticated Watchport session plus CSRF protection.

## 8. Start the host indicator

Run:

```bash
watchport-indicator
```

When healthy and idle it normally hides itself. If a viewer is active it becomes an always-on-top warning with viewer count, elapsed time, and a local **Disconnect viewers** control.

Do not rely on manual startup for permanent use. Once the live tests pass, configure the gateway and indicator to start automatically and restart on failure using the host OS's service/supervision mechanism.

## 9. Discover the Sunshine host and Desktop app

With Sunshine paired to Moonlight-Web, run:

```bash
watchport-doctor
```

It exercises only Moonlight-Web's local control API and lists paired hosts. Put the intended host UUID into:

```text
WATCHPORT_MOONLIGHT_HOST_UUID=<uuid>
```

Run `watchport-doctor` again. It then lists apps for that host. Put the Desktop app ID into:

```text
WATCHPORT_MOONLIGHT_APP_ID=<id>
```

Restart Watchport and the indicator after changing configuration.

## 10. Publish the Moonlight player path to the tailnet only

This is intentionally a live-integration step rather than a guessed static recipe. Moonlight-Web signaling and WebRTC media behavior must be observed on the actual version/platform.

Requirements:

- the browser must reach Moonlight-Web at `WATCHPORT_STREAM_ORIGIN`
- Moonlight-Web's own public Internet Access/rendezvous remains OFF
- traffic must remain tailnet-only
- direct WebRTC/UDP should be preferred where it materially lowers latency
- no public router port-forward is created
- Tailscale policy permits only the minimum verified TCP/UDP ports

Use `tailscale status`, Moonlight-Web logs, browser WebRTC diagnostics, and the acceptance checklist to determine whether traffic is direct or relayed.

## 11. Do not call it ready yet

After setup, complete every applicable item in [`LIVE-ACCEPTANCE.md`](LIVE-ACCEPTANCE.md). The most important tests deliberately kill the browser, indicator, gateway, network path, and Moonlight capability while watching whether the host warning and stream behave correctly.
