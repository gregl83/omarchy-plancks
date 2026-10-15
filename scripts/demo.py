#!/usr/bin/env python3
"""Render a scripted production-UI demo in an active Omarchy Wayland session."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import plancks
import sessions
from preview_environment import stage_desktop


def stage_fixture(root):
    """Seed real storage and stage production components, without live settings."""
    shell = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
    stage_desktop(root)
    for name in ('Ui', 'Commons'):
        (root / name).symlink_to(shell / name)
    now = datetime(2026, 10, 15, 13, 37, tzinfo=ZoneInfo('America/Los_Angeles'))
    base = plancks.clock()

    def stamp(date):
        utc = round(date.timestamp() * 1000)
        return dict(base, utcMs=utc, bootMs=base['bootMs'] + utc - base['utcMs'])

    store = plancks.Store(root / 'state' / 'omarchy' / 'gregl83.plancks')
    sequence = 0
    # Varied, deterministic activity makes the calendar and recent-session trend
    # reviewable without reading or modifying the user's history.
    for day in range(84, 7, -1):
        start = (now - timedelta(days=day)).replace(hour=9, minute=0)
        if start.weekday() >= 5 or day % 11 == 0:
            continue
        state, _ = store.transition('start', f'sample-start-{day}', sequence, now=stamp(start))
        duration = (18, 42, 75, 130, 55)[day % 5]
        config = dict(sessions.DEFAULTS, preset='custom', name='Reading' if day % 2 else 'Focus',
                      focusMinutes=duration, rounds=1, finalBreak=False)
        state, _ = store.session_action('session_started', f'sample-session-{day}', state['sequence'],
                                       config=config, now=stamp(start))
        current = state['session']
        stopped = day % 9 == 0
        state, _ = store.session_action('session_stopped' if stopped else 'session_completed',
            f'sample-finish-{day}', state['sequence'], session_id=current['sessionId'],
            stage_id=current['stages'][0]['stageId'],
            now=stamp(start + timedelta(minutes=duration // 2 if stopped else duration)))
        if day % 13 == 0:
            state, _ = store.session_action('session_inclusion_changed', f'sample-exclude-{day}',
                state['sequence'], session_id=current['sessionId'], excluded=True,
                now=stamp(start + timedelta(hours=3)))
        state, _ = store.transition('end', f'sample-end-{day}', state['sequence'],
                                   now=stamp(start + timedelta(hours=8)))
        sequence = state['sequence']
    for day in range(7, -1, -1):
        start = (now - timedelta(days=day)).replace(hour=9, minute=0)
        sequence += 1
        store.transition('start', f'demo-start-{day}', sequence - 1, now=stamp(start))
        if day:
            sequence += 1
            store.transition('end', f'demo-end-{day}', sequence - 1,
                             now=stamp(start + timedelta(hours=[8, 8, 8.25, 7.75, 8.5, 7.5, 8, 8][day])))
    # Advance a fixed sample date at normal speed. UI animations remain genuine.
    helper = root / 'demo_clock.py'
    helper.write_text(
        'import sys, time\nsys.path.insert(0, ' + repr(str(REPO)) + ')\n'
        'import plancks\nbase = ' + repr(stamp(now)) + '\n'
        'origin = time.monotonic()\n'
        'def clock():\n'
        '    elapsed = round((time.monotonic() - origin) * 1000)\n'
        '    return dict(base, utcMs=base["utcMs"] + elapsed, bootMs=base["bootMs"] + elapsed)\n'
        'plancks.clock = clock\nplancks.serve(plancks.Store())\n')
    plugin = root / 'Plancks'
    plugin.mkdir()
    for path in REPO.iterdir():
        if path.suffix in ('.qml', '.js', '.py') or path.name in ('qmldir', 'assets'):
            if path.name != 'EpochController.qml':
                if path.name in ('EpochPanel.qml', 'HistoryView.qml', 'SessionHistory.qml'):
                    # Relative date labels use the same date as the sample clock.
                    (plugin / path.name).write_text(path.read_text().replace(
                        'new Date()', f'new Date({round(now.timestamp() * 1000)})'))
                else:
                    (plugin / path.name).symlink_to(path)
    controller = (REPO / 'EpochController.qml').read_text()
    command = next(line for line in controller.splitlines() if line.strip().startswith('command: ["python3", "-u"'))
    (plugin / 'EpochController.qml').write_text(controller.replace(
        command, '    command: ' + json.dumps([sys.executable, '-u', str(helper)])))


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=REPO / 'assets' / 'demo')
    parser.add_argument('--fps', type=int, default=20, choices=(15, 20, 25, 30))
    parser.add_argument('--keep-frames', action='store_true', help='Keep captured PNGs for inspection')
    args = parser.parse_args()
    for command in ('quickshell', 'ffmpeg'):
        if not shutil.which(command):
            parser.error(f'{command} is required')
    if not os.environ.get('WAYLAND_DISPLAY'):
        parser.error('Run in an active Omarchy Wayland session')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='plancks-demo-') as directory:
        root = Path(directory)
        stage_fixture(root)
        frames = root / 'frames'
        frames.mkdir()
        qml = (REPO / 'scripts' / 'demo.qml').read_text()
        qml = qml.replace('DEMO_FRAMES', json.dumps(str(frames)))
        qml = qml.replace('DEMO_FPS', str(args.fps))
        (root / 'shell.qml').write_text(qml)
        env = dict(os.environ, XDG_STATE_HOME=str(root / 'state'),
                   PLANCKS_DISABLE_NOTIFICATIONS='1', TZ='America/Los_Angeles')
        print('Capturing scripted production UI…', flush=True)
        result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        (output / 'render.log').write_text(result.stdout)
        if result.returncode or 'DEMO_PASS' not in result.stdout or any(
                marker in result.stdout for marker in ('DEMO_FAIL', ' ERROR', 'WARN scene:')):
            raise RuntimeError(f'Demo render failed; see {output / "render.log"}\n{result.stdout}')
        print(result.stdout, flush=True)
        count = int(re.search(r'DEMO_PASS frames=(\d+)', result.stdout).group(1))
        captured = sorted(path.name for path in frames.glob('*.png'))
        if not count or captured != [f'{index:05d}.png' for index in range(count)]:
            raise RuntimeError('Incomplete frame sequence; refusing to encode partial media')
        common = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y']
        video = root / 'plancks.mp4'
        gif = root / 'plancks.gif'
        run(common + ['-framerate', str(args.fps), '-i', str(frames / '%05d.png'),
                      '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                      '-movflags', '+faststart', str(video)])
        # A shared palette and rectangle dithering keep stationary text clean.
        run(common + ['-i', str(video), '-filter_complex',
                      'fps=15,scale=960:-2:flags=lanczos,split[a][b];'
                      '[a]palettegen=stats_mode=diff[p];'
                      '[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle',
                      '-loop', '0', str(gif)])
        shutil.copy2(frames / f'{3 * args.fps:05d}.png', output / 'poster.png')
        shutil.copy2(video, output / video.name)
        shutil.copy2(gif, output / gif.name)
        if args.keep_frames:
            shutil.copytree(frames, output / 'frames', dirs_exist_ok=True)
        for path in (output / video.name, output / gif.name):
            print(f'{path}: {path.stat().st_size / 1024 / 1024:.1f} MiB')


if __name__ == '__main__':
    main()
