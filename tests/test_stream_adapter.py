import pytest

from watchport.stream_adapter import MoonlightWebAdapter, StreamAdapterError


class FakeTransport:
    def __init__(self, *, local_only=True, permissions=None):
        self.local_only = local_only
        self.permissions = permissions or {"gamepad": False, "keyboardMouse": False}
        self.calls = []
        self.cookie = "player-cookie"
        self.logged_in = False

    def login_local_owner(self):
        self.calls.append(("login",))
        self.logged_in = True

    def logout_owner(self):
        self.calls.append(("logout",))
        self.logged_in = False

    def deactivate(self, slot):
        self.calls.append(("deactivate", slot))
        return {"slot": slot, "state": "off"}

    def set_viewer_permissions(self, slot):
        self.calls.append(("permissions", slot))
        return {"slot": slot, "permissions": dict(self.permissions)}

    def activate(self, slot, host_uuid, app_id, ttl_secs):
        self.calls.append(("activate", slot, host_uuid, app_id, ttl_secs))
        return {
            "slot": slot,
            "url": f"https://192.168.1.9/p/token-{slot}",
            "pin": "123456",
            "local_only": self.local_only,
            "access_level": "viewer",
            "permissions": dict(self.permissions),
        }

    def redeem_player(self, token, pin):
        self.calls.append(("redeem", token, pin))
        return self.cookie

    def status(self):
        return {"slots": []}

    def hosts(self):
        return []

    def apps(self, host_uuid):
        return []


def adapter(fake, slots=(2, 3, 4)):
    return MoonlightWebAdapter(
        control_origin="https://127.0.0.1",
        stream_origin="https://desktop.example.ts.net",
        slots=slots,
        host_uuid="host-uuid",
        app_id=7,
        ttl_seconds=3600,
        transport=fake,
    )


def test_open_mints_viewer_and_redeems_cookie_locally():
    fake = FakeTransport()
    a = adapter(fake)
    grant = a.open("session-a", now=100)
    assert grant.slot == 2
    assert grant.viewer_url == "https://desktop.example.ts.net/p/token-2"
    assert grant.cookie_name == "mw_player"
    assert grant.cookie_value == "player-cookie"
    assert grant.cookie_max_age == 3600
    assert ("permissions", 2) in fake.calls
    assert ("redeem", "token-2", "123456") in fake.calls
    assert fake.calls[-1] == ("logout",)


def test_open_is_idempotent_for_same_watchport_session():
    fake = FakeTransport()
    a = adapter(fake)
    first = a.open("session-a")
    call_count = len(fake.calls)
    second = a.open("session-a")
    assert second == first
    assert len(fake.calls) == call_count


def test_each_session_gets_distinct_dedicated_player_slot():
    fake = FakeTransport()
    a = adapter(fake, slots=(2, 3))
    assert a.open("a").slot == 2
    assert a.open("b").slot == 3
    with pytest.raises(StreamAdapterError, match="slots are in use"):
        a.open("c")


def test_close_kills_slot_before_forgetting_grant():
    fake = FakeTransport()
    a = adapter(fake)
    grant = a.open("session-a")
    assert a.close("session-a") is True
    assert ("deactivate", grant.slot) in fake.calls
    assert a.grant_for("session-a") is None
    assert a.close("session-a") is False


def test_public_moonlight_rendezvous_is_refused_and_revoked():
    fake = FakeTransport(local_only=False)
    a = adapter(fake)
    with pytest.raises(StreamAdapterError, match="Internet Access must be disabled"):
        a.open("session-a")
    # One pre-clean and one cleanup after the unsafe activation was detected.
    assert fake.calls.count(("deactivate", 2)) >= 2
    assert a.grant_for("session-a") is None


def test_any_input_permission_is_refused():
    fake = FakeTransport(permissions={"gamepad": False, "keyboardMouse": True})
    a = adapter(fake)
    with pytest.raises(StreamAdapterError, match="Viewer-only permissions"):
        a.open("session-a")
    assert a.grant_for("session-a") is None


def test_cleanup_reclaims_all_owned_slots():
    fake = FakeTransport()
    a = adapter(fake, slots=(2, 3, 4))
    a.cleanup_stale_slots()
    for slot in (2, 3, 4):
        assert ("deactivate", slot) in fake.calls
