"""Local Mac setup and launchd lifecycle. Never exposed over HTTP."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import secrets
import shlex
import subprocess
import sys

from .config import Settings
from .doctor import _adapter

LABELS = {'gateway': 'net.watchport.gateway', 'indicator': 'net.watchport.indicator'}


def private_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(data)


def make_plist(role: str, python: Path, config: Path, data_dir: Path) -> dict:
    module = 'watchport.app' if role == 'gateway' else 'watchport.indicator'
    return {
        'Label': LABELS[role], 'ProgramArguments': [str(python), '-m', module],
        'EnvironmentVariables': {'WATCHPORT_CONFIG_FILE': str(config)},
        'WorkingDirectory': str(data_dir), 'RunAtLoad': True, 'KeepAlive': True,
        'ThrottleInterval': 3, 'LimitLoadToSessionType': 'Aqua', 'Umask': 0o077,
        'StandardOutPath': str(data_dir / f'{role}.log'),
        'StandardErrorPath': str(data_dir / f'{role}.log'),
    }


def launchctl(*args: str, check: bool = True):
    result = subprocess.run(['launchctl', *args], capture_output=True, text=True, timeout=20)
    if check and result.returncode:
        # Do not print launchctl's environment dump or private paths.
        raise RuntimeError(f'launchctl {args[0]} failed (exit {result.returncode})')
    return result


def init_config(path: Path, hostname: str, port: int) -> None:
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.ts\.net', hostname):
        raise ValueError('use the actual device MagicDNS hostname ending in .ts.net')
    if not 1024 <= port <= 65535:
        raise ValueError('local gateway port must be between 1024 and 65535')
    values = {
        'WATCHPORT_HOST': '127.0.0.1', 'WATCHPORT_PORT': str(port),
        'WATCHPORT_ORIGIN': f'https://{hostname}:8443', 'WATCHPORT_RP_ID': hostname,
        'WATCHPORT_STREAM_ORIGIN': f'https://{hostname}:9443',
        'WATCHPORT_INDICATOR_SECRET': secrets.token_urlsafe(32),
        'WATCHPORT_DATA_DIR': str(path.parent), 'WATCHPORT_COOKIE_SECURE': 'true',
        'WATCHPORT_MOONLIGHT_ORIGIN': 'https://127.0.0.1',
        'WATCHPORT_MOONLIGHT_HOST_UUID': '', 'WATCHPORT_MOONLIGHT_APP_ID': '-1',
        'WATCHPORT_MOONLIGHT_SLOTS': '2,3,4', 'WATCHPORT_MOONLIGHT_TTL': '3600',
        'WATCHPORT_LOCAL_URL': f'http://127.0.0.1:{port}',
    }
    private_write(path, ('# Private Watchport configuration. Never commit this file.\n' + '\n'.join(f'{k}={shlex.quote(v)}' for k, v in values.items()) + '\n').encode())
    print(f'Created private configuration: {path}')
    print('Next: verify Moonlight ports, host UUID and Desktop app ID; run watchport-doctor.')


def install(config: Path, settings: Settings, directory: Path, dry_run: bool) -> None:
    # Do not resolve the venv Python symlink: its path selects the venv packages.
    python = Path(sys.executable).absolute()
    if not dry_run:
        if platform.system() != 'Darwin':
            raise RuntimeError('launchd installation requires macOS')
        result = subprocess.run([str(python), '-c', 'import tkinter'], capture_output=True, timeout=10)
        if result.returncode:
            raise RuntimeError('this Python needs working Tk; install matching python-tk before continuing')
        if not settings.stream_configured:
            raise RuntimeError('configure and validate the real Moonlight host/app first')
        _adapter(settings).probe()  # checks Internet Access is explicitly disabled
    directory.mkdir(parents=True, exist_ok=True)
    targets = {role: directory / f'{label}.plist' for role, label in LABELS.items()}
    if any(path.exists() for path in targets.values()):
        raise RuntimeError('Watchport plists already exist; use the documented stop/upgrade procedure')
    for role, path in targets.items():
        private_write(path, plistlib.dumps(make_plist(role, python, config, settings.data_dir)))
    if dry_run:
        print('Generated two plists; no services started.')
        return
    domain = f'gui/{os.getuid()}'
    loaded = []
    try:
        for role, path in targets.items():
            launchctl('bootstrap', domain, str(path))
            loaded.append(role)
        for label in LABELS.values():
            launchctl('print', f'{domain}/{label}')
    except Exception:
        for role in loaded:
            launchctl('bootout', f'{domain}/{LABELS[role]}', check=False)
        # Preserve generated files for diagnosis; no destructive reset.
        raise
    print('Gateway and indicator registered in the logged-in GUI session. Run live acceptance next.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('~/.watchport/config.env'))
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--hostname', required=True)
    init.add_argument('--port', type=int, default=8787)
    install_cmd = sub.add_parser('install')
    install_cmd.add_argument('--dry-run', action='store_true')
    install_cmd.add_argument('--output', type=Path)
    sub.add_parser('status')
    sub.add_parser('uninstall')
    args = parser.parse_args()
    config = args.config.expanduser().absolute()
    try:
        if args.command == 'init':
            init_config(config, args.hostname, args.port)
            return
        os.environ['WATCHPORT_CONFIG_FILE'] = str(config)
        settings = Settings.from_env()
        directory = Path.home() / 'Library/LaunchAgents'
        if args.command == 'install':
            if args.dry_run and not args.output:
                raise RuntimeError('--dry-run requires --output to keep previews outside LaunchAgents')
            install(config, settings, args.output.expanduser().absolute() if args.output else directory, args.dry_run)
            return
        if platform.system() != 'Darwin':
            raise RuntimeError('service status/uninstall requires macOS')
        domain = f'gui/{os.getuid()}'
        if args.command == 'status':
            print(json.dumps({role: {'loaded': launchctl('print', f'{domain}/{label}', check=False).returncode == 0} for role, label in LABELS.items()}, indent=2))
            return
        # Prevent new admissions, retain the indicator until revocation succeeds.
        service = f'{domain}/{LABELS["gateway"]}'
        if launchctl('print', service, check=False).returncode == 0:
            launchctl('bootout', service)
        _adapter(settings).cleanup_stale_slots()
        service = f'{domain}/{LABELS["indicator"]}'
        if launchctl('print', service, check=False).returncode == 0:
            launchctl('bootout', service)
        for label in LABELS.values():
            (directory / f'{label}.plist').unlink(missing_ok=True)
        print('Viewer slots confirmed off; Watchport agents removed. Private configuration and passkeys retained.')
    except Exception as exc:
        print(f'Watchport host setup: {exc}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
