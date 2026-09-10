from dataclasses import replace
from threading import Event, Thread
import time
import pytest

from fastapi.testclient import TestClient
from test_app_security import settings
from test_stream_adapter import FakeTransport
from watchport.app import create_app
from watchport.stream_adapter import StreamAdapterError


def running(tmp_path):
    config = replace(settings(tmp_path), moonlight_host_uuid='host', moonlight_app_id=7, indicator_timeout_seconds=1)
    app = create_app(config)
    state = app.state.watchport
    state['adapter'].transport = FakeTransport()
    session = state['sessions'].create()
    return app, state, session


def post_start(client, session):
    client.cookies.set('watchport_session', session.token)
    return client.post('/api/view/start', headers={'X-Watchport-CSRF': session.csrf})


def acknowledge(indicator, stop):
    while not stop.wait(0.01):
        indicator.heartbeat(rendered_token=indicator.snapshot()['displayToken'])


def test_no_upstream_capability_before_warning_ack(tmp_path):
    app, state, session = running(tmp_path)
    with TestClient(app, base_url='https://desktop.example.ts.net:8443') as client:
        state['indicator'].heartbeat()
        response = post_start(client, session)
        assert response.status_code == 503
        assert not any(c[0] == 'activate' for c in state['adapter'].transport.calls)
        assert state['indicator'].viewer_count() == 0


def test_start_waits_for_render_and_logout_revokes(tmp_path):
    app, state, session = running(tmp_path)
    stop = Event()
    with TestClient(app, base_url='https://desktop.example.ts.net:8443') as client:
        state['indicator'].heartbeat()
        thread = Thread(target=acknowledge, args=(state['indicator'], stop))
        thread.start()
        try:
            response = post_start(client, session)
            assert response.status_code == 200
            assert 'mw_player=' in response.headers['set-cookie']
            assert state['indicator'].confirmed(session.token)
            response = client.post('/api/logout', headers={'X-Watchport-CSRF': session.csrf})
            assert response.status_code == 200
            assert state['adapter'].grant_for(session.token) is None
            assert state['indicator'].viewer_count() == 0
        finally:
            stop.set()
            thread.join()


def test_expiry_after_upstream_minting_revokes_grant(tmp_path):
    app, state, session = running(tmp_path)
    original = state['adapter'].open
    def expire_after_mint(*args, **kwargs):
        grant = original(*args, **kwargs)
        session.expires_at = time.time() - 1
        return grant
    state['adapter'].open = expire_after_mint
    stop = Event()
    with TestClient(app, base_url='https://desktop.example.ts.net:8443') as client:
        state['indicator'].heartbeat()
        thread = Thread(target=acknowledge, args=(state['indicator'], stop))
        thread.start()
        try:
            response = post_start(client, session)
            assert response.status_code == 503
            assert 'mw_player' not in response.headers.get('set-cookie', '')
            assert state['adapter'].grant_for(session.token) is None
        finally:
            stop.set()
            thread.join()


def test_host_kill_retains_warning_until_orphan_slot_is_confirmed_off(tmp_path):
    app, state, session = running(tmp_path)
    transport = state['adapter'].transport
    deactivate = transport.deactivate
    def fail_one_slot(slot):
        if slot == 2:
            raise StreamAdapterError('slot cannot be confirmed off')
        return deactivate(slot)
    transport.deactivate = fail_one_slot
    with pytest.raises(StreamAdapterError):
        state['adapter'].cleanup_stale_slots()
    # An uncertain capability need not have a local STREAMING session.
    state['indicator'].viewer_start(session.token)
    client = TestClient(app, base_url='https://desktop.example.ts.net:8443', client=('127.0.0.1', 12345))
    headers = {'X-Watchport-Indicator': state['settings'].indicator_secret}
    response = client.post('/internal/indicator/kill', headers=headers)
    assert response.status_code == 503
    assert state['indicator'].viewer_count() == 1
    assert state['adapter'].uncertain
    transport.deactivate = deactivate
    response = client.post('/internal/indicator/kill', headers=headers)
    assert response.status_code == 200
    assert state['indicator'].viewer_count() == 0
    assert not state['adapter'].uncertain
