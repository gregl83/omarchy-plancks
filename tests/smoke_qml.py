#!/usr/bin/env python3
"""Run the actual widget/controller in an isolated Quickshell on Wayland.

Does not alter the user's bar or epoch history. Pass --preview to briefly
show a test widget and open its panel as part of the smoke test.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preview', action='store_true')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
shell = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
with tempfile.TemporaryDirectory(prefix='plancks-smoke-') as directory:
    root = Path(directory)
    for name in ('Ui', 'Commons'):
        (root / name).symlink_to(shell / name)
    (root / 'Plancks').symlink_to(repo)
    (root / 'shell.qml').write_text('''import QtQuick
import Quickshell
import "Plancks" as Plancks
ShellRoot {
  id: test
  property int step: 0
  property int attempts: 0
  property bool preview: PREVIEW
  function check(condition, message) {
    if (!condition) { console.error("SMOKE_FAIL " + message); Qt.quit(); }
    return condition
  }
  PanelWindow {
    visible: test.preview
    implicitWidth: 280
    implicitHeight: 40
    exclusionMode: ExclusionMode.Ignore
    color: "#202020"
    Plancks.Widget { id: widget; width: implicitWidth; height: implicitHeight; settings: ({initialSeconds: 1}) }
  }
  Plancks.Widget { id: second; width: implicitWidth; height: implicitHeight; settings: ({initialSeconds: 1}) }
  Timer {
    interval: 600
    repeat: true
    running: true
    onTriggered: {
      test.attempts++
      if (!test.check(test.attempts < 18, "helper timeout: " + Plancks.EpochController.error)) return
      if (!Plancks.EpochController.ready || Plancks.EpochController.busy) return
      if (test.step === 0) {
        if (!test.check(widget.epoch.phase === "off", "initial phase")) return
        Plancks.EpochController.transition()
        test.step = 1
      } else if (test.step === 1) {
        if (!test.check(widget.epoch.phase === "active" && second.epoch.phase === "active", "shared active epoch")) return
        if (test.preview) widget.open()
        test.step = 2
      } else if (test.step === 2) {
        if (widget.epoch.timer.indexOf("+") !== 0) return
        if (!test.check(widget.epoch.indicator === "●", "overrun keeps active phase")) return
        Plancks.EpochController.transition()
        test.step = 3
      } else if (test.step === 3) {
        if (!test.check(widget.epoch.phase === "off" && second.epoch.phase === "off", "shared end transition")) return
        if (!test.check(widget.epoch.workSampleCount === 1, "completed sample")) return
        second.bar = verticalBar
        if (!test.check(second.vertical && second.implicitHeight > 40, "vertical layout")) return
        Plancks.EpochController.reset()
        test.step = 4
      } else {
        if (!test.check(widget.epoch.phase === "off" && second.epoch.sequence === 0, "shared reset")) return
        if (!test.check(widget.epoch.workSampleCount === 0 && widget.epoch.lastStartUtcMs === null, "reset clears history")) return
        widget.close()
        console.log("PLANCKS_SMOKE_PASS: two widgets, start, overrun, end, vertical layout, reset")
        Qt.quit()
      }
    }
  }
  QtObject {
    id: verticalBar
    property bool vertical: true
    property int barSize: 32
    property color barForeground: "white"
    property color foreground: "white"
    property color urgent: "red"
    property string position: "left"
    property bool foregroundAnimationEnabled: false
    property string fontFamily: "monospace"
    function hideTooltip(item) {}
    function unregisterClickTarget(item) {}
    function registerClickTarget(item) {}
  }
}
'''.replace('PREVIEW', 'true' if args.preview else 'false'))
    env = dict(os.environ, XDG_STATE_HOME=str(root / 'state'))
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'],
                            env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=20)
    print(result.stdout)
    if result.returncode or 'PLANCKS_SMOKE_PASS' not in result.stdout or 'SMOKE_FAIL' in result.stdout or ' ERROR' in result.stdout or 'WARN scene:' in result.stdout:
        raise SystemExit(1)
