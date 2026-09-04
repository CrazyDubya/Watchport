import pytest
from watchport.sessions import SessionManager, State


def test_indicator_required_for_admission():
    mgr = SessionManager(900, 300)
    s = mgr.create(now=10)
    with pytest.raises(PermissionError):
        mgr.admit(s, False, now=11)
    assert s.state == State.AUTHENTICATED


def test_admission_expires_closed_to_stream_start():
    mgr = SessionManager(900, 5)
    s = mgr.create(now=10)
    mgr.admit(s, True, now=11)
    with pytest.raises(PermissionError):
        mgr.start_stream(s, now=17)


def test_valid_lifecycle_and_viewer_heartbeat():
    mgr = SessionManager(900, 300)
    s = mgr.create(now=10)
    mgr.admit(s, True, now=11)
    mgr.start_stream(s, now=12)
    assert s.state == State.STREAMING
    assert s.viewer_last_seen_at == 12
    mgr.touch_viewer(s, now=15)
    assert s.viewer_last_seen_at == 15
    mgr.stop_stream(s)
    assert s.state == State.AUTHENTICATED
    assert s.viewer_last_seen_at == 0
    mgr.close(s)
    assert mgr.get(s.token, now=16) is None


def test_expired_stream_remains_reapable_until_external_revoke():
    mgr = SessionManager(10, 5)
    s = mgr.create(now=10)
    mgr.admit(s, True, now=11)
    mgr.start_stream(s, now=12)
    assert mgr.get(s.token, now=21) is None
    # The HTTP auth path treats it as expired, but the watchdog can still see it
    # and revoke its external capability before deleting session state.
    assert mgr.streaming() == [s]
    mgr.close(s)
    assert mgr.streaming() == []


def test_touch_rejects_non_streaming_session():
    mgr = SessionManager(900, 300)
    s = mgr.create(now=10)
    with pytest.raises(PermissionError):
        mgr.touch_viewer(s, now=11)


def test_double_admission_is_rejected():
    mgr = SessionManager(900, 300)
    s = mgr.create(now=10)
    mgr.admit(s, True, now=11)
    with pytest.raises(PermissionError):
        mgr.admit(s, True, now=12)
