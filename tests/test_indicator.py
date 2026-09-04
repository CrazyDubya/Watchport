from watchport.indicator_state import IndicatorState


def test_indicator_health_times_out():
    indicator = IndicatorState('secret-secret-secret-secret', 5)
    assert not indicator.healthy(now=10)
    indicator.heartbeat(now=10)
    assert indicator.healthy(now=15)
    assert not indicator.healthy(now=15.01)


def test_viewer_count_is_idempotent_and_tracks_oldest_start():
    indicator = IndicatorState('secret-secret-secret-secret', 5)
    indicator.viewer_start('a', now=20)
    indicator.viewer_start('a', now=25)
    indicator.viewer_start('b', now=30)
    assert indicator.viewer_count() == 2
    assert indicator.oldest_started_at() == 20
    indicator.viewer_stop('a')
    assert indicator.viewer_count() == 1
    assert set(indicator.active_sessions) == {'b'}
    assert indicator.oldest_started_at() == 30
    indicator.clear()
    assert indicator.viewer_count() == 0
    assert indicator.oldest_started_at() is None
