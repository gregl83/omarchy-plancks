#!/usr/bin/env python3
"""Render the marketplace showcase from production UI assets and components."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from preview_environment import stage_desktop

REPO = Path(__file__).resolve().parents[1]
SHELL = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
with tempfile.TemporaryDirectory(prefix='plancks-showcase-') as directory:
    root = Path(directory)
    stage_desktop(root)
    for name in ('Commons', 'Ui'):
        (root / name).symlink_to(SHELL / name)
    (root / 'Plancks').symlink_to(REPO)
    (root / 'assets').symlink_to(REPO / 'assets')
    qml = (REPO / 'scripts/showcase.qml').read_text()
    qml = qml.replace('SHOWCASE_PATH', json.dumps(str(REPO / 'preview.png')))
    (root / 'shell.qml').write_text(qml)
    env = dict(os.environ, PLANCKS_DISABLE_NOTIFICATIONS='1', XDG_STATE_HOME=str(root / 'state'))
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    print(result.stdout)
    if result.returncode or 'SHOWCASE_PASS' not in result.stdout or ' ERROR' in result.stdout:
        raise SystemExit(1)
