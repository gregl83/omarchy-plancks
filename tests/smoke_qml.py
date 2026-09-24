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
    (root / 'shell.qml').write_text(r'''import QtQuick
import Quickshell
import QtTest
import Quickshell.Io
import "Plancks" as Plancks
ShellRoot {
  id: test
  property bool resetUiDone: false
  property int step: 0
  property bool ipcDone: true
  Process {
    id: ipcCall
    command: ["qs", "ipc", "-n", "-p", decodeURIComponent(Qt.resolvedUrl(".").toString().replace(/^file:\/\//, "")),
              "call", "--", "gregl83.plancks", "toggleEpoch"]
    property string reply: ""
    stdout: SplitParser { onRead: function(line) { ipcCall.reply += line.trim() } }
    onExited: function(code, status) {
      if (!test.check(code === 0 && reply === "submitted", "IPC response: " + reply)) return
      reply = ""
      test.ipcDone = true
    }
  }
  function toggleViaIpc() {
    ipcDone = false
    ipcCall.running = true
  }
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
      if (!test.ipcDone || !Plancks.EpochController.ready || Plancks.EpochController.busy) return
      if (test.step === 0) {
        if (!test.check(widget.epoch.phase === "off", "initial phase")) return
        Plancks.EpochController.busy = true
        if (!test.check(Plancks.EpochController.ipc.toggleEpoch() === "busy", "IPC busy guard")) return
        Plancks.EpochController.busy = false
        Plancks.EpochController.ready = false
        if (!test.check(Plancks.EpochController.ipc.toggleEpoch() === "not-ready", "IPC readiness guard")) return
        Plancks.EpochController.ready = true
        test.toggleViaIpc()
        test.step = 1
      } else if (test.step === 1) {
        if (!test.check(widget.epoch.phase === "active" && second.epoch.phase === "active", "shared active epoch")) return
        if (test.preview) widget.open()
        test.step = 2
      } else if (test.step === 2) {
        if (widget.epoch.timer.indexOf("+") !== 0) return
        if (!test.check(widget.epoch.indicator === "●", "overrun keeps active phase")) return
        test.toggleViaIpc()
        test.step = 3
      } else if (test.step === 3) {
        if (!test.check(widget.epoch.phase === "off" && second.epoch.phase === "off", "shared end transition")) return
        if (!test.check(widget.epoch.workSampleCount === 1, "completed sample")) return
        second.bar = verticalBar
        if (!test.check(second.vertical && second.implicitHeight > 40, "vertical layout")) return
        if (!test.preview) Plancks.EpochController.reset()
        test.step = 4
      } else {
        if (test.preview && !test.resetUiDone) return
        if (!test.check(widget.epoch.phase === "off" && second.epoch.sequence === 0, "shared reset")) return
        if (!test.check(widget.epoch.workSampleCount === 0 && widget.epoch.lastStartUtcMs === null, "reset clears history")) return
        widget.close()
        console.log("PLANCKS_SMOKE_PASS: two widgets, IPC start/end, IPC guards, overrun, vertical layout, reset")
        Qt.quit()
      }
    }
  }
  // Keep QtTest from quitting before the outer smoke check verifies both widgets.
  TestCase { name: "SmokeLifetime"; when: false }
  TestCase {
    id: resetTest
    name: "ResetConfirmation"
    when: test.preview && test.step === 4
    function test_resetConfirmation() {
      var panel = findChild(widget, "plancks_root")
      verify(panel !== null, "Find the production panel")
      var keys = findChild(panel, "plancks_keys")
      verify(keys !== null)
      // QtTest sends keys to its containing window: use the actual popup.
      parent = keys
      var action = findChild(panel, "plancks_actionButton")
      var reset = findChild(panel, "plancks_resetButton")
      var cancel = findChild(panel, "plancks_cancelButton")
      var confirm = findChild(panel, "plancks_confirmButton")
      var warning = findChild(panel, "plancks_resetWarning")
      var scroll = findChild(panel, "plancks_scroll")
      wait(300)
      keys.forceActiveFocus()
      keyClick(Qt.Key_Tab)
      verify(action.activeFocus, "Tab reaches epoch action")
      keyClick(Qt.Key_Tab)
      verify(reset.activeFocus, "Tab reaches reset")
      wait(100)
      verify(reset.mapToItem(scroll.contentItem, 0, 0).y + reset.height <= scroll.contentY + scroll.height + 1,
             "Reset scrolls into view")
      var sequence = Plancks.EpochController.state.sequence
      var generation = Plancks.EpochController.state.generation
      function unchanged() {
        compare(Plancks.EpochController.state.sequence, sequence)
        compare(Plancks.EpochController.state.generation, generation)
        compare(Plancks.EpochController.state.workSampleCount, 1)
        verify(!Plancks.EpochController.busy)
      }
      keyClick(Qt.Key_Return)
      verify(panel.confirmingReset)
      verify(warning.visible)
      verify(warning.text.indexOf("This cannot be undone") >= 0)
      verify(cancel.activeFocus, "Cancel is the default")
      unchanged()
      keyClick(Qt.Key_Return)
      verify(!panel.confirmingReset, "Activating Cancel dismisses warning")
      verify(reset.activeFocus)
      wait(150)
      unchanged()
      keyClick(Qt.Key_Return)
      keyClick(Qt.Key_Tab)
      verify(confirm.activeFocus)
      keyClick(Qt.Key_Escape)
      verify(!panel.confirmingReset, "Escape cancels even on the destructive button")
      verify(reset.activeFocus)
      wait(150)
      unchanged()
      keyClick(Qt.Key_Return)
      keyClick(Qt.Key_Tab)
      verify(confirm.activeFocus)
      keyClick(Qt.Key_Return)
      tryVerify(function() { return Plancks.EpochController.state.sequence === 0 && !Plancks.EpochController.busy })
      verify(!panel.confirmingReset)
      verify(Plancks.EpochController.state.generation !== generation)
      compare(Plancks.EpochController.state.workSampleCount, 0)
      console.log("PLANCKS_RESET_UI_PASS")
      test.resetUiDone = true
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
    if result.returncode or 'PLANCKS_SMOKE_PASS' not in result.stdout or 'SMOKE_FAIL' in result.stdout or ' ERROR' in result.stdout or 'WARN scene:' in result.stdout or 'FAIL!' in result.stdout or (args.preview and 'PLANCKS_RESET_UI_PASS' not in result.stdout):
        raise SystemExit(1)
