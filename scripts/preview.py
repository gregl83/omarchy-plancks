#!/usr/bin/env python3
"""Capture the README panels and marketplace showcase with frozen sample history."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import plancks
from preview_environment import stage_desktop

shell = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
now = datetime.now().astimezone().replace(hour=13, minute=37, second=0, microsecond=0)
base = plancks.clock()


def stamp(date):
    utc = round(date.timestamp() * 1000)
    return dict(base, utcMs=utc, bootMs=base['bootMs'] + utc - base['utcMs'])


with tempfile.TemporaryDirectory(prefix='plancks-preview-') as directory:
    root = Path(directory)
    stage_desktop(root)
    state_dir = root / 'state' / 'omarchy' / 'gregl83.plancks'
    store = plancks.Store(state_dir)
    sequence = 0
    for day in range(6, -1, -1):
        start = (now - timedelta(days=day)).replace(hour=9, minute=0)
        sequence += 1
        store.transition('start', f'start-{day}', sequence - 1, now=stamp(start))
        if day:
            sequence += 1
            store.transition('end', f'end-{day}', sequence - 1,
                             now=stamp(start + timedelta(hours={6: 7.5, 5: 8.5, 4: 7.75, 3: 8.25, 2: 8, 1: 8}[day])),
                             skip_learning=day == 1)
    helper = root / 'frozen.py'
    helper.write_text('import sys\nsys.path.insert(0, ' + repr(str(REPO)) + ')\n'
                      'import plancks\nplancks.clock = lambda: ' + repr(stamp(now)) + '\n'
                      'plancks.serve(plancks.Store())\n')
    for name in ('Ui', 'Commons'):
        (root / name).symlink_to(shell / name)
    plugin = root / 'Plancks'
    plugin.mkdir()
    for name in ('qmldir', 'Widget.qml', 'EpochPanel.qml', 'HistoryView.qml', 'HistoryTrend.qml', 'AnimatedGraphic.qml', 'CoffeeGraphic.qml', 'StarshipGraphic.qml', 'InsightsSettings.qml', 'insights.py', 'GraphicPreview.qml', 'Graphics.js', 'plancks.py'):
        (plugin / name).symlink_to(REPO / name)
    controller = (REPO / 'EpochController.qml').read_text()
    command = next(line for line in controller.splitlines() if line.strip().startswith('command: ["python3"'))
    controller = controller.replace(command, '    command: ' + json.dumps([sys.executable, '-u', str(helper)]))
    (plugin / 'EpochController.qml').write_text(controller)
    qml = r'''import QtQuick
import QtQuick.Window
import Quickshell
import QtTest
import qs.Commons
import "Plancks" as Plancks
import "PreviewContext.js" as Desktop
ShellRoot {
  id: capture
  property var card: null
  property int step: 0
  property int attempts: 0
  QtObject {
    id: bar
    property bool vertical: false
    property int barSize: Style.bar.sizeHorizontal
    property color foreground: Color.foreground
    property color barForeground: Color.foreground
    property color urgent: Color.urgent
    property string position: "top"
    property bool foregroundAnimationEnabled: false
    property bool hidden: false
    property var activePopout: null
    function requestPopout(item) { activePopout = item }
    function releasePopout(item) { if (activePopout === item) activePopout = null }
    property string fontFamily: Style.font.family
    function hideTooltip(item) {}
    function showTooltip(item, text) {}
    function registerClickTarget(item) {}
    function unregisterClickTarget(item) {}
  }
  PanelWindow {
    id: window
    visible: true
    screen: Quickshell.screens.find(function(screen) { return screen.name === Desktop.screenName })
    implicitWidth: stage.width
    implicitHeight: stage.height
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    Item {
      id: stage
      width: Style.space(380) + Style.gapsOut * 2
      height: capture.card ? capture.card.y + capture.card.height + Style.gapsOut : 600
      PreviewWallpaper {
        id: wallpaper
        anchors.fill: parent
      }
      Rectangle {
        width: parent.width
        height: bar.barSize
        color: Color.bar.background
        Item {
          anchors.fill: parent
          Text {
            height: parent.height
            text: CLOCK
            anchors.right: widget.left
            anchors.rightMargin: Style.space(8)
            color: Color.foreground
            verticalAlignment: Text.AlignVCenter
            font.family: Style.font.family
            font.pixelSize: Style.font.body
          }
          Plancks.Widget {
            id: widget
            anchors.horizontalCenter: parent.horizontalCenter
            bar: bar
            width: implicitWidth
            height: bar.barSize
            Rectangle {
              anchors.bottom: parent.bottom
              anchors.horizontalCenter: parent.horizontalCenter
              width: widget.openPanelIndicatorWidth
              height: Style.space(2)
              radius: 1
              color: Color.accent
            }
          }
          Text {
            height: parent.height
            text: "☼"
            anchors.left: widget.right
            anchors.leftMargin: Style.space(8)
            color: Color.foreground
            verticalAlignment: Text.AlignVCenter
            font.family: Style.font.family
            font.pixelSize: Style.font.icon
          }
        }
      }
    }
  }
  TestCase { id: lookup; name: "PreviewLookup"; when: false }
  function find(item, name) { return lookup.findChild(item, name) }
  function save(path, nextStep) {
    var started = stage.grabToImage(function(result) {
      if (!result.saveToFile(path)) { console.error("PREVIEW_FAIL saving " + path); Qt.quit(); return }
      console.log("PREVIEW_SAVED " + path)
      capture.step = nextStep
    }, Qt.size(Math.round(stage.width * 3.2 / window.devicePixelRatio), Math.round(stage.height * 3.2 / window.devicePixelRatio)))
    if (!started) { console.error("PREVIEW_FAIL capture"); Qt.quit() }
  }
  Timer {
    interval: 250
    repeat: true
    running: true
    onTriggered: {
      if (++capture.attempts > 80) { console.error("PREVIEW_FAIL timeout: " + Plancks.EpochController.error); Qt.quit(); return }
      if (!Plancks.EpochController.ready || !wallpaper.ready) return
      var panel = find(widget, "plancks_root")
      if (capture.step === 0) { widget.open(); capture.step = 1; return }
      if (capture.step === 1) {
        var keys = find(panel, "plancks_keys")
        capture.card = keys.parent.parent
        capture.card.parent = stage
        capture.card.x = Style.gapsOut
        capture.card.y = bar.barSize + Style.gapsOut
        // The card is staged outside its popup; keep popup fades out of captures.
        capture.card.opacity = 1
        capture.step = 2
        return
      }
      if (capture.step === 2) { capture.step = -1; capture.save(MAIN_PATH, 3); return }
      if (capture.step === 3) { panel.openHistory(); capture.step = 4; return }
      if (capture.step === 4 && !Plancks.EpochController.historyLoading) {
        capture.step = -1
        capture.save(HISTORY_PATH, 5)
        return
      }
      if (capture.step === 5) { panel.openSettings(); capture.step = 6; return }
      if (capture.step === 6) {
        find(panel, "plancks_graphicPreviewTimer").stop()
        find(panel, "plancks_settingsView").previewElapsed = 5800
        capture.step = 7
        return
      }
      if (capture.step === 7) { capture.step = -1; capture.save(SETTINGS_PATH, 8); return }
      if (capture.step === 8) { console.log("PREVIEW_PASS"); Qt.quit() }
    }
  }
}
'''
    qml = qml.replace('CLOCK', json.dumps(now.strftime('%A %H:%M')))
    qml = qml.replace('MAIN_PATH', json.dumps(str(REPO / 'assets/preview-main.png')))
    qml = qml.replace('HISTORY_PATH', json.dumps(str(REPO / 'assets/preview-history.png')))
    qml = qml.replace('SETTINGS_PATH', json.dumps(str(REPO / 'assets/preview-settings.png')))
    (root / 'shell.qml').write_text(qml)
    env = dict(os.environ, XDG_STATE_HOME=str(root / 'state'))
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    print(result.stdout)
    if result.returncode or 'PREVIEW_PASS' not in result.stdout or 'PREVIEW_FAIL' in result.stdout or ' ERROR' in result.stdout or 'WARN scene:' in result.stdout:
        raise SystemExit(1)

subprocess.run([sys.executable, str(REPO / "scripts/showcase.py")], check=True)
