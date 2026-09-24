#!/usr/bin/env python3
"""Check release metadata and, when supplied, a release tag's version and ancestry."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def validate(tag=None):
    manifest = json.loads(Path('manifest.json').read_text())
    for key in ('id', 'name', 'version', 'author', 'description'):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f'manifest.json requires a nonempty {key}')
    version = manifest['version']
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('Use a stable MAJOR.MINOR.PATCH manifest version')
    for name in ('README.md', 'LICENSE', 'preview.png', 'qmldir', 'plancks.py',
                 'Widget.qml', 'EpochPanel.qml', 'EpochController.qml'):
        if not Path(name).is_file() or Path(name).stat().st_size == 0:
            raise ValueError(f'Missing or empty package file: {name}')
    if tag is not None:
        if tag != f'v{version}':
            raise ValueError(f'Release tag must be v{version}, matching manifest.json')
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        tagged = subprocess.check_output(['git', 'rev-parse', f'refs/tags/{tag}^{{commit}}'], text=True).strip()
        if tagged != head:
            raise ValueError('Release tag does not point to the checked-out commit')
        ancestry = subprocess.run(['git', 'merge-base', '--is-ancestor', head, 'origin/main'])
        if ancestry.returncode != 0:
            raise ValueError('Release commit must be reachable from origin/main')
    print(f'Package metadata valid: {manifest["id"]} {version}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', help='Require this tag to match the version and a commit on origin/main')
    args = parser.parse_args()
    try:
        validate(args.tag)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Validation failed: {exc}\n')
