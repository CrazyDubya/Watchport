from watchport.bootstrap import BootstrapToken


def test_bootstrap_token_is_stable_then_consumed(tmp_path):
    bootstrap = BootstrapToken(tmp_path)
    first = bootstrap.ensure()
    second = bootstrap.ensure()
    assert first == second
    assert len(first) >= 32
    assert bootstrap.verify(first)
    assert not bootstrap.verify(first + "x")
    bootstrap.consume()
    assert not bootstrap.verify(first)


def test_consuming_missing_bootstrap_token_is_idempotent(tmp_path):
    BootstrapToken(tmp_path).consume()
