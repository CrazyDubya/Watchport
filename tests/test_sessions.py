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


def test_valid_lifecycle():
    mgr = SessionManager(900, 300)
    s = mgr.create(now=10)
    mgr.admit(s, True, now=11)
    mgr.start_stream(s, now=12)
    assert s.state == State.STREAMING
    mgr.close(s)
    assert mgr.get(s.token, now=13) is None
