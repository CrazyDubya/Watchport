# Run the current V1

1. Install Python 3.12 and create a virtual environment.
2. Install Watchport in editable mode with dev dependencies: `pip install -e '.[dev]'`.
3. Copy `.env.example` into your shell environment and replace `WATCHPORT_INDICATOR_SECRET` with a long random value.
4. Install/configure Sunshine and Moonlight-Web separately. Create a backend-enforced **Viewer** invitation; do not use Gamer or Full Control.
5. Set `WATCHPORT_VIEWER_URL` to that viewer invitation URL.
6. Start the gateway with `watchport`.
7. Start the host indicator in the logged-in desktop session with `watchport-indicator`.
8. From the host itself, open Watchport and enroll the first passkey. Enrollment intentionally fails for non-loopback clients.
9. Expose Watchport only through your Tailscale path and HTTPS. Set `WATCHPORT_ORIGIN` and `WATCHPORT_RP_ID` to the exact HTTPS hostname used by the browser before enrolling a passkey.
10. From a Tailnet-authorized phone/laptop, open Watchport, authenticate with the passkey, and start the view.

## Important

The current adapter opens an externally managed Moonlight-Web Viewer invitation after Watchport admission. It does not yet revoke that external invitation when indicator liveness fails. See `BUILD_STATUS.md`. Do not treat this build as production-ready until external stream revocation is wired into the adapter.
