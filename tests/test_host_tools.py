from pathlib import Path
import os
import plistlib
import pytest
from watchport.host import init_config, make_plist
from watchport.config import Settings
from watchport.acceptance import CHECKS, initialize, summarize


def test_mac_plist_keeps_venv_path_and_secrets_out_of_arguments():
    config = Path('/Users/test user/.watchport/config.env')
    python = Path('/Users/test user/Watchport/.venv/bin/python')
    item = make_plist('indicator', python, config, config.parent)
    parsed = plistlib.loads(plistlib.dumps(item))
    assert parsed['ProgramArguments'] == [str(python), '-m', 'watchport.indicator']
    assert parsed['EnvironmentVariables'] == {'WATCHPORT_CONFIG_FILE': str(config)}
    assert parsed['KeepAlive'] is True
    assert parsed['LimitLoadToSessionType'] == 'Aqua'
    assert parsed['Umask'] == 0o077


def test_config_init_is_private_and_never_overwrites_credentials(tmp_path, monkeypatch):
    path = tmp_path / 'config.env'
    init_config(path, 'desktop.example.ts.net', 8787)
    first = path.read_bytes()
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        init_config(path, 'desktop.example.ts.net', 8787)
    assert path.read_bytes() == first
    for key in list(os.environ):
        if key.startswith('WATCHPORT_'):
            monkeypatch.delenv(key)
    monkeypatch.setenv('WATCHPORT_CONFIG_FILE', str(path))
    settings = Settings.from_env()
    assert settings.port == 8787
    assert settings.origin == 'https://desktop.example.ts.net:8443'
    assert settings.stream_origin == 'https://desktop.example.ts.net:9443'
    assert len(settings.indicator_secret) >= 32
    monkeypatch.delenv('WATCHPORT_PORT')
    monkeypatch.delenv('WATCHPORT_STREAM_ORIGIN')
    path.write_text('\n'.join(line for line in path.read_text().splitlines()
        if not line.startswith(('WATCHPORT_PORT=', 'WATCHPORT_STREAM_ORIGIN='))) + '\n')
    defaults = Settings.from_env()
    assert defaults.port == settings.port
    assert defaults.stream_origin == settings.stream_origin


@pytest.mark.parametrize('player_port', [0, 443, 8443, 65536])
def test_config_init_rejects_invalid_or_shared_https_port(tmp_path, player_port):
    path = tmp_path / 'config.env'
    with pytest.raises(ValueError, match='player HTTPS port'):
        init_config(path, 'desktop.example.ts.net', 8787, player_port)
    assert not path.exists()


def test_config_init_accepts_an_explicit_player_port(tmp_path):
    path = tmp_path / 'config.env'
    init_config(path, 'desktop.example.ts.net', 8787, 10443)
    assert 'WATCHPORT_STREAM_ORIGIN=https://desktop.example.ts.net:10443' in path.read_text()


def test_shell_syntax_in_config_is_never_executed(tmp_path, monkeypatch):
    path = tmp_path / 'config.env'
    marker = tmp_path / 'must-not-exist'
    path.write_text(f"WATCHPORT_INDICATOR_SECRET='$(touch {marker})'\n")
    path.chmod(0o600)
    monkeypatch.setenv('WATCHPORT_CONFIG_FILE', str(path))
    monkeypatch.delenv('WATCHPORT_INDICATOR_SECRET', raising=False)
    from watchport.config import load_config_file
    load_config_file()
    assert not marker.exists()
    assert os.environ['WATCHPORT_INDICATOR_SECRET'].startswith('$(touch')


@pytest.mark.parametrize('stream_origin', ['https://desktop.example.ts.net:8443', 'https://desktop.example.ts.net:443/path', 'https://user@desktop.example.ts.net'])
def test_config_rejects_player_origin_escape(tmp_path, monkeypatch, stream_origin):
    path = tmp_path / 'config.env'
    init_config(path, 'desktop.example.ts.net', 8787)
    for key in list(os.environ):
        if key.startswith('WATCHPORT_'):
            monkeypatch.delenv(key)
    monkeypatch.setenv('WATCHPORT_CONFIG_FILE', str(path))
    monkeypatch.setenv('WATCHPORT_STREAM_ORIGIN', stream_origin)
    with pytest.raises(RuntimeError):
        Settings.from_env()


def test_control_lock_excludes_another_process(tmp_path):
    import subprocess
    import sys
    from watchport.control_lock import control_lock
    path = tmp_path / 'control.lock'
    code = 'from pathlib import Path; from watchport.control_lock import control_lock; import sys\nwith control_lock(Path(sys.argv[1]), timeout=0.1): pass'
    with control_lock(path):
        result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True)
        assert result.returncode != 0
        assert b'TimeoutError' in result.stderr
    result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True)
    assert result.returncode == 0


def test_missing_live_evidence_cannot_be_ready():
    report = initialize('version', 'commit', 'version', 'iPhone Safari', 'Chrome')
    assert not summarize(report)['ready']
    for case in report['checks'].values():
        case.update(status='pass', evidence='observed on target host')
    assert not summarize(report)['ready']
    for network in ('lan', 'cellular', 'remote'):
        for _ in range(5):
            report['measurements'].append({'network': network, 'path': 'direct', 'profile': '1080p30 H264', 'first_frame_ms': 1000, 'glass_to_glass_ms': 100, 'reconnect_ms': 2000, 'readable': True})
    assert summarize(report)['ready']
    del report['checks']['both_killed']
    assert not summarize(report)['ready']
