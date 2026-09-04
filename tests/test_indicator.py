from watchport.indicator_state import IndicatorState


def test_indicator_health_times_out():
    indicator = IndicatorState('secret', 5)
    assert not indicator.healthy(now=10)
    indicator.heartbeat(now=10)
    assert indicator.healthy(now=15)
    assert not indicator.healthy(now=15.01)


def test_viewer_count_is_idempotent():
    indicator = IndicatorState('secret', 5)
    indicator.viewer_start('a')
    indicator.viewer_start('a')
    indicator.viewer_start('b')
    assert len(indicator.active_sessions) == 2
    indicator.viewer_stop('a')
    assert indicator.active_sessions == {'b'}
