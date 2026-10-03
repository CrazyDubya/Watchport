"""Record real-host acceptance evidence; missing evidence never means ready."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess

CHECKS = {
    'private_perimeter': 'Gateway, signaling and media inaccessible without authorized Tailscale access',
    'management_isolation': 'No Moonlight admin/owner endpoint or owner cookie reachable through the player ingress',
    'desktop_identity': 'Shared host/app remains the configured Desktop, including an unrelated owner stream attempt',
    'passkey_iphone': 'Real iPhone Safari enrollment, authentication and cancellation on the final HTTPS hostname',
    'passkey_desktop': 'Real desktop browser passkey authentication',
    'bootstrap_replay': 'Wrong, missing and consumed bootstrap tokens rejected',
    'origin_replay': 'Wrong-origin and expired authorization rejected',
    'view_only': 'Keyboard, mouse, touch, gamepad and crafted input packets cannot control the host',
    'warning_before_pixels': 'Host warning visibly precedes first usable frame',
    'indicator_kill': 'Killing indicator stops video and invalidates old player authority',
    'indicator_ui_stall': 'Stalling only the GUI event loop stops video even if network thread survives',
    'gateway_kill': 'Killing gateway causes independent revocation',
    'both_killed': 'Simultaneous process death recovers with bounded measured residual viewing',
    'partial_revoke': 'One failed slot remains unsafe, warning retained, further admission blocked',
    'session_expiry': 'Expiry, Close view, local Disconnect viewers and Lock all revoke external authority',
    'phone_lifecycle': 'Phone lock, backgrounding, duplicate tabs and Wi-Fi/cellular transitions reclaim old slots safely',
    'host_lifecycle': 'Host sleep/wake, screen lock, logout/login and reboot have safe observed behavior',
    'recovery': 'Clean install, launchd restart, stop/upgrade and credential recovery verified',
    'privacy': 'Logs/report contain no desktop content, credentials, PINs, cookies or private keys',
}
NETWORKS = ('lan', 'cellular', 'remote')


def initialize(sunshine: str, moonlight: str, tailscale: str, iphone: str, desktop: str) -> dict:
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5)
    return {
        'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'versions': {'watchport_commit': result.stdout.strip() if result.returncode == 0 else 'unknown',
                     'host_os': platform.platform(), 'python': platform.python_version(),
                     'sunshine': sunshine, 'moonlight_commit': moonlight, 'tailscale': tailscale,
                     'iphone_browser': iphone, 'desktop_browser': desktop},
        'checks': {key: {'description': description, 'status': 'not_run', 'evidence': ''} for key, description in CHECKS.items()},
        'measurements': [],
        'targets': {'first_frame_ms': 2500, 'glass_to_glass_ms': {'lan': 150, 'cellular': 300, 'remote': 300}, 'reconnect_ms': 5000, 'minimum_samples_per_network': 5},
    }


def percentile95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)]


def summarize(report: dict) -> dict:
    blockers = []
    for key in CHECKS:
        item = report.get('checks', {}).get(key, {})
        if item.get('status') != 'pass' or not item.get('evidence', '').strip():
            blockers.append(key)
    for key in ('watchport_commit', 'host_os', 'sunshine', 'moonlight_commit', 'tailscale', 'iphone_browser', 'desktop_browser'):
        if report.get('versions', {}).get(key, '').lower() in ('', 'unknown', 'not_run'):
            blockers.append('version:' + key)
    results = {}
    targets = report['targets']
    for network in NETWORKS:
        rows = [row for row in report.get('measurements', []) if row['network'] == network]
        if len(rows) < targets['minimum_samples_per_network']:
            blockers.append('measurements:' + network)
        if not rows:
            continue
        stats = {field: {'median': statistics.median(row[field] for row in rows), 'p95': percentile95([row[field] for row in rows])} for field in ('first_frame_ms', 'glass_to_glass_ms', 'reconnect_ms')}
        results[network] = {'samples': len(rows), 'metrics': stats}
        for field in stats:
            limit = targets[field][network] if field == 'glass_to_glass_ms' else targets[field]
            if stats[field]['p95'] > limit:
                blockers.append(f'performance:{network}:{field}')
        if any(not row['readable'] for row in rows):
            blockers.append('readability:' + network)
    return {'ready': not blockers, 'blockers': blockers, 'networks': results}


def save(path: Path, report: dict) -> None:
    # Reports stay private until deliberately sanitized for docs/research.
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as file:
        temporary.chmod(0o600)
        json.dump(report, file, indent=2)
        file.write('\n')
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for name in ('sunshine', 'moonlight-commit', 'tailscale', 'iphone', 'desktop'):
        init.add_argument('--' + name, required=True)
    check = sub.add_parser('check')
    check.add_argument('case', choices=CHECKS)
    check.add_argument('--status', choices=('pass', 'fail', 'blocked'), required=True)
    check.add_argument('--evidence', required=True, help='Sanitized observation, elapsed time and result; no secrets')
    measure = sub.add_parser('measure')
    measure.add_argument('--network', choices=NETWORKS, required=True)
    measure.add_argument('--path', choices=('direct', 'derp'), required=True)
    measure.add_argument('--profile', required=True, help='Actual codec/resolution/FPS/bitrate observed')
    for name in ('first-frame-ms', 'glass-to-glass-ms', 'reconnect-ms'):
        measure.add_argument('--' + name, type=float, required=True)
    measure.add_argument('--readable', choices=('yes', 'no'), required=True)
    sub.add_parser('summary')
    args = parser.parse_args()
    path = args.report.expanduser()
    if args.command == 'init':
        if path.exists():
            parser.error('report already exists; preserve its evidence')
        path.parent.mkdir(parents=True, exist_ok=True)
        report = initialize(args.sunshine, args.moonlight_commit, args.tailscale, args.iphone, args.desktop)
    else:
        report = json.loads(path.read_text())
        if report.get('schema') != 1:
            parser.error('unsupported report schema')
        if args.command == 'check':
            if not args.evidence.strip():
                parser.error('evidence is required')
            report['checks'][args.case].update(status=args.status, evidence=args.evidence, recorded_at=datetime.now(timezone.utc).isoformat())
        elif args.command == 'measure':
            values = [args.first_frame_ms, args.glass_to_glass_ms, args.reconnect_ms]
            if not all(math.isfinite(value) and value > 0 for value in values):
                parser.error('enter positive, finite measurements from the real stream')
            report['measurements'].append({'network': args.network, 'path': args.path, 'profile': args.profile,
                'first_frame_ms': values[0], 'glass_to_glass_ms': values[1], 'reconnect_ms': values[2], 'readable': args.readable == 'yes'})
        else:
            summary = summarize(report)
            print(json.dumps(summary, indent=2))
            raise SystemExit(0 if summary['ready'] else 1)
    save(path, report)
    print(f'Recorded {args.command}; readiness requires all observations and measurements.')


if __name__ == '__main__':
    main()
