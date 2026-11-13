#!/usr/bin/env python3
"""Exercise the production timestamp editor against isolated real storage."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
import plancks

shell = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
with tempfile.TemporaryDirectory(prefix='plancks-edit-check-') as directory:
    root = Path(directory)
    for name in ('Ui', 'Commons'):
        (root / name).symlink_to(shell / name)
    (root / 'Plancks').symlink_to(repo)
    now = plancks.clock()
    store = plancks.Store(root / 'state/omarchy/gregl83.plancks')
    for i, (action, hours) in enumerate([('start', 4), ('end', 3), ('start', 2)]):
        stamp = dict(now, utcMs=now['utcMs'] - hours * 3600000, bootMs=now['bootMs'] - hours * 3600000)
        store.transition(action, 'sample-' + str(i), i, now=stamp)
    (root / 'shell.qml').write_text('''import QtQuick
import QtQuick.Window
import Quickshell
import QtTest
import "Plancks" as Plancks
Window {
  id: window
  visible: true; width: 540; height: 900
  property bool done: false
  Timer { interval: 100; running: window.done; onTriggered: Qt.quit() }
  Timer {
    interval: 100; running: true; repeat: true
    onTriggered: if (Plancks.EpochController.ready && !Plancks.EpochController.historyLoading && !Plancks.EpochController.history.total) Plancks.EpochController.requestHistory(0)
  }
  Plancks.HistoryView { id: history; anchors.fill: parent }
  TestCase {
    name: "HistoryTimes"
    when: Plancks.EpochController.ready && Plancks.EpochController.history.total > 0
    function find(item, name) {
      if (item.objectName === name) return item
      var children = item.children || []
      for (var i = 0; i < children.length; i++) { var child = find(children[i], name); if (child) return child }
      return null
    }
    function verify(value, message) { if (!value) throw new Error(message) }
    function compare(actual, expected, message) { verify(actual === expected, message + ": " + actual + " != " + expected) }
    function test_editor() {
      try {
        wait(200)
        var trigger = find(history, "plancks_historyEdit_0")
        verify(!!trigger, "Edit button exists")
        trigger.forceActiveFocus()
        verify(trigger.activeFocus, "Edit button accepts keyboard focus")
        trigger.clicked()
        var editor = find(history, "plancks_historyTimeEditor")
        var start = find(editor, "plancks_editStart")
        var save = find(editor, "plancks_saveTimes")
        wait(50)
        verify(editor.visible && start.activeFocus, "Clicked field focused")
        verify(!save.enabled, "Opening editor preserves exact milliseconds: " + start.text + " / " + editor.startMs + " vs " + editor.sample.start.utcMs + " formatted=" + editor.stamp(editor.sample.start.utcMs) + " end " + editor.endMs + " vs " + editor.sample.end.utcMs)
        verify(!isFinite(editor.parse("2026-02-30T12:00:00+00:00")), "Invalid date rejected")
        verify(!isFinite(editor.parse("2026-11-01T12:00:00+15:00")), "Invalid UTC offset rejected")
        var original = editor.sample.start.utcMs
        start.text = "invalid"
        verify(!save.enabled, "Invalid draft cannot save")
        start.text = editor.stamp(original + 900000)
        verify(save.enabled, "Valid correction enables save")
        save.clicked()
        tryCompare(editor, "visible", false, 5000)
        tryCompare(Plancks.EpochController, "historyLoading", false, 5000)
        verify(Plancks.EpochController.history.rows[0].edited, "Saved correction marked")
        var edited = Plancks.EpochController.history.rows[0]
        compare(edited.start.utcMs, Plancks.EpochController.history.rows[1].end.utcMs, "Shared boundary updated")
        find(history, "plancks_historyEdit_0").clicked()
        find(editor, "plancks_restoreTimes").clicked()
        save.clicked()
        tryCompare(editor, "visible", false, 5000)
        tryCompare(Plancks.EpochController, "historyLoading", false, 5000)
        compare(Plancks.EpochController.history.rows[0].start.utcMs, original, "Restores original precision")
        verify(!Plancks.EpochController.history.rows[0].edited, "Restored marker cleared")
        find(history, "plancks_historyEdit_0").clicked()
        var sequence = Plancks.EpochController.state.sequence
        find(editor, "plancks_cancelTimes").clicked()
        verify(!editor.visible, "Cancel returns to history")
        compare(Plancks.EpochController.state.sequence, sequence, "Cancel writes nothing")
        console.log("HISTORY_EDIT_PASS")
      } catch (error) { console.error("HISTORY_EDIT_FAIL " + error) }
      window.done = true
    }
  }
}''')
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'],
        env=dict(os.environ, XDG_STATE_HOME=str(root / 'state'), PLANCKS_DISABLE_NOTIFICATIONS='1'),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
    if result.returncode or 'HISTORY_EDIT_PASS' not in result.stdout or 'HISTORY_EDIT_FAIL' in result.stdout or 'FAIL!' in result.stdout:
        raise SystemExit(result.stdout)
    print('History editor passed: focus, validation, shared-boundary save, restore, and cancel.')
