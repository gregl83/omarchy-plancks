#!/usr/bin/env python3
"""Measure every attributed quote with Qt's notification text layout, offscreen."""
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from insights import QUOTES

# Omarchy NotificationCard: 380 - 2*2 border - 2*12 padding - 40 icon - 12 gap.
# Also check 280px to leave room for slightly denser themes than the 300px default.
with tempfile.TemporaryDirectory(prefix='plancks-quote-check-') as directory:
    root = Path(directory)
    bodies = {key: html.escape(f'“{quote}” — {author}')
              for key, (quote, author, _) in QUOTES.items()}
    (root / 'shell.qml').write_text('''import QtQuick
import QtQuick.Window
Window {
  visible: true
  width: 400; height: 200
  property var bodies: BODIES
  Text {
    id: body
    font.family: "Liberation Sans"
    textFormat: Text.StyledText
    wrapMode: Text.WordWrap
    elide: Text.ElideRight
    maximumLineCount: 3
  }
  Timer {
    interval: 150; running: true
    onTriggered: {
      var failures = []
      if (Qt.fontFamilies().indexOf("Liberation Sans") < 0)
        failures.push("Liberation Sans is missing; install ttf-liberation")
      for (var scale of [1, 1.25, 1.5, 2]) {
        for (var available of [280, 300]) {
          body.width = Math.round(available * scale)
          body.font.pixelSize = Math.round(14 * scale)
          for (var key in bodies) {
            body.text = bodies[key]
            body.forceLayout()
            if (body.truncated || body.contentWidth > body.width)
              failures.push(key + " at " + available + "px / " + scale + "x")
          }
        }
      }
      if (failures.length) console.error("QUOTE_FIT_FAIL: " + failures.join(", "))
      else console.log("QUOTE_FIT_PASS")
      Qt.quit()
    }
  }
}'''.replace('BODIES', json.dumps(bodies)))
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    if result.returncode or 'QUOTE_FIT_PASS' not in result.stdout:
        raise SystemExit(result.stdout)
    print(f'All {len(QUOTES)} attributed quotes fit three lines at 280/300px and 1–2× scale.')
