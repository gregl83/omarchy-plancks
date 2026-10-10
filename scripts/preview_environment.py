"""Supply the active Omarchy wallpaper and focused monitor to isolated renders."""
import json
from pathlib import Path
import shutil
import subprocess


def stage_desktop(root):
    wallpaper = Path.home() / '.local/state/omarchy/current/background'
    wallpaper = wallpaper.resolve(strict=True)
    monitors = json.loads(subprocess.check_output(['hyprctl', 'monitors', '-j'], text=True))
    monitors = [monitor for monitor in monitors if not monitor.get('disabled', False)]
    if not monitors:
        raise RuntimeError('Preview generation requires an active monitor')
    monitor = next((monitor for monitor in monitors if monitor.get('focused')), monitors[0])
    width, height = monitor['width'], monitor['height']
    if monitor.get('transform', 0) in (1, 3, 5, 7):
        width, height = height, width
    scale = monitor['scale']
    values = {'wallpaper': wallpaper.as_uri(), 'screenName': monitor['name'],
              'width': width / scale, 'height': height / scale}
    context = '.pragma library\n' + '\n'.join(
        f'var {key} = {json.dumps(value)}' for key, value in values.items()) + '\n'
    (root / 'PreviewContext.js').write_text(context)
    shutil.copyfile(Path(__file__).with_name('PreviewWallpaper.qml'), root / 'PreviewWallpaper.qml')
    print(f'Preview desktop: {monitor["name"]}, {values["width"]:g} × {values["height"]:g} logical pixels')
