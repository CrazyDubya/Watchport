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

    def internet_status(self):
        return {"internet_access_enabled": False, "upnp_enabled": False}

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


def test_partial_cleanup_preserves_unrevoked_grant_and_blocks_admission():
    fake = FakeTransport()
    a = adapter(fake)
    grant = a.open('a')
    deactivate = fake.deactivate
    def partial(slot):
        if slot == grant.slot:
            raise StreamAdapterError('unreachable slot')
        return deactivate(slot)
    fake.deactivate = partial
    with pytest.raises(StreamAdapterError, match='1 Watchport-owned'):
        a.cleanup_stale_slots()
    assert a.grant_for('a') == grant
    assert a.uncertain
    with pytest.raises(StreamAdapterError, match='unresolved'):
        a.open('b')
    fake.deactivate = deactivate
    a.cleanup_stale_slots()
    assert not a.uncertain
    assert a.active_count() == 0


def test_successful_http_response_is_not_proof_of_revocation():
    fake = FakeTransport()
    a = adapter(fake)
    grant = a.open('a')
    fake.deactivate = lambda slot: {'slot': slot, 'state': 'binded'}
    with pytest.raises(StreamAdapterError, match='confirm'):
        a.close('a')
    assert a.grant_for('a') == grant
    assert a.uncertain


def test_failed_activation_and_failed_cleanup_block_future_admission():
    fake = FakeTransport(local_only=False)
    a = adapter(fake)
    calls = 0
    def deactivate(slot):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise StreamAdapterError('cannot revoke')
        return {'slot': slot, 'state': 'off'}
    fake.deactivate = deactivate
    with pytest.raises(StreamAdapterError):
        a.open('a')
    assert a.uncertain
    with pytest.raises(StreamAdapterError, match='unresolved'):
        a.open('b')


def test_disconnected_rendezvous_does_not_override_enabled_internet_setting():
    fake = FakeTransport(local_only=True)
    fake.internet_status = lambda: {'internet_access_enabled': True}
    a = adapter(fake)
    with pytest.raises(StreamAdapterError, match='configuration check'):
        a.open('a')
    assert not any(c[0] == 'activate' for c in fake.calls)


@pytest.mark.parametrize('upnp', [True, None, 0, 'false'])
def test_enabled_or_unverified_upnp_blocks_probe_and_activation(upnp):
    fake = FakeTransport()
    fake.internet_status = lambda: {'internet_access_enabled': False, 'upnp_enabled': upnp}
    a = adapter(fake)
    for operation in (a.probe, lambda: a.open('a')):
        with pytest.raises(StreamAdapterError, match='UPnP must be disabled'):
            operation()
        assert not fake.logged_in
    assert not any(call[0] in {'activate', 'redeem'} for call in fake.calls)
    assert a.grant_for('a') is None


def test_missing_upnp_status_does_not_prove_private_configuration():
    fake = FakeTransport()
    fake.internet_status = lambda: {'internet_access_enabled': False}
    with pytest.raises(StreamAdapterError, match='UPnP must be disabled'):
        adapter(fake).open('a')
    assert not any(call[0] == 'activate' for call in fake.calls)


def test_v024_activation_without_local_only_is_rejected_and_revoked():
    # Source-derived response shape from v0.2.4 (b7e1f66); synthetic credentials.
    # That release ignores host_uuid/app_id/ttl_secs and omits local_only.
    # This regression proves refusal, not live compatibility or video teardown.
    fake = FakeTransport()
    activation = fake.activate

    def legacy_activate(*args):
        result = activation(*args)
        del result['local_only']
        return result

    fake.activate = legacy_activate
    a = adapter(fake)
    with pytest.raises(StreamAdapterError, match='incompatible upstream contract'):
        a.open('a')
    assert fake.calls.count(('deactivate', 2)) == 2
    assert not any(call[0] == 'redeem' for call in fake.calls)
    assert a.grant_for('a') is None
    assert not a.uncertain
