from pathlib import Path
import pytest

from watchport.config import Settings


def base_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WATCHPORT_INDICATOR_SECRET", "x" * 32)
    monkeypatch.setenv("WATCHPORT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WATCHPORT_ORIGIN", "https://desktop.example.ts.net:8443")
    monkeypatch.setenv("WATCHPORT_RP_ID", "desktop.example.ts.net")
    monkeypatch.setenv("WATCHPORT_STREAM_ORIGIN", "https://desktop.example.ts.net")
    monkeypatch.setenv("WATCHPORT_MOONLIGHT_ORIGIN", "https://127.0.0.1")


def test_secure_defaults_are_loopback_and_unconfigured(monkeypatch, tmp_path):
    base_env(monkeypatch, tmp_path)
    settings = Settings.from_env()
    assert settings.host == "127.0.0.1"
    assert settings.cookie_secure is True
    assert settings.stream_configured is False
    assert settings.moonlight_slots == (2, 3, 4)


def test_gateway_refuses_non_loopback_bind(monkeypatch, tmp_path):
    base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCHPORT_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError, match="bind to loopback"):
        Settings.from_env()


def test_stream_origin_must_share_watchport_hostname(monkeypatch, tmp_path):
    base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCHPORT_STREAM_ORIGIN", "https://different.example.ts.net")
    with pytest.raises(RuntimeError, match="same hostname"):
        Settings.from_env()


def test_moonlight_control_must_be_loopback(monkeypatch, tmp_path):
    base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCHPORT_MOONLIGHT_ORIGIN", "https://192.168.1.9")
    with pytest.raises(RuntimeError, match="loopback"):
        Settings.from_env()


def test_indicator_secret_has_minimum_length(monkeypatch, tmp_path):
    base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCHPORT_INDICATOR_SECRET", "short")
    with pytest.raises(RuntimeError, match="at least 24"):
        Settings.from_env()


def test_only_moonlight_player_slots_are_allowed(monkeypatch, tmp_path):
    base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCHPORT_MOONLIGHT_SLOTS", "1,2")
    with pytest.raises(RuntimeError, match="player slots"):
        Settings.from_env()
