from fastapi.testclient import TestClient

from watchport.app import create_app
from watchport.config import Settings


def settings(tmp_path):
    return Settings(
        host="127.0.0.1",
        port=8443,
        origin="https://desktop.example.ts.net:8443",
        rp_id="desktop.example.ts.net",
        data_dir=tmp_path,
        cookie_secure=True,
        session_ttl_seconds=900,
        admission_ttl_seconds=60,
        viewer_heartbeat_timeout_seconds=12,
        indicator_timeout_seconds=6,
        indicator_secret="x" * 32,
        moonlight_origin="https://127.0.0.1",
        stream_origin="https://desktop.example.ts.net",
        moonlight_slots=(2, 3, 4),
        moonlight_host_uuid="",
        moonlight_app_id=-1,
        moonlight_ttl_seconds=3600,
        moonlight_verify_tls=False,
    )


def client(tmp_path):
    app = create_app(settings(tmp_path))
    return TestClient(app, base_url="https://desktop.example.ts.net:8443")


def test_security_headers_are_present(tmp_path):
    with client(tmp_path) as c:
        response = c.get("/")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert "object-src 'none'" in response.headers["content-security-policy"]


def test_unauthenticated_view_start_is_refused(tmp_path):
    with client(tmp_path) as c:
        response = c.post("/api/view/start")
        assert response.status_code == 401


def test_first_passkey_options_require_bootstrap_token(tmp_path):
    with client(tmp_path) as c:
        response = c.post("/api/passkeys/register/options")
        assert response.status_code == 403


def test_valid_bootstrap_token_can_request_registration_options(tmp_path):
    with client(tmp_path) as c:
        token = (tmp_path / "bootstrap-token").read_text().strip()
        response = c.post(
            "/api/passkeys/register/options", headers={"X-Watchport-Bootstrap": token}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["challengeKey"]
        assert body["options"]["rp"]["id"] == "desktop.example.ts.net"


def test_untrusted_host_header_is_rejected(tmp_path):
    with client(tmp_path) as c:
        response = c.get("/", headers={"host": "attacker.example"})
        assert response.status_code == 400
