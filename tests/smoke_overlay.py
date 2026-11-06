#!/usr/bin/env python3
"""Exercise overlay timing, session priority and non-interactive window properties."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
shell = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell'
with tempfile.TemporaryDirectory(prefix='plancks-overlay-check-') as directory:
    root = Path(directory)
    (root / 'Commons').symlink_to(shell / 'Commons')
    for name in ('TimerOverlay.qml', 'OverlayLogic.js'):
        shutil.copy2(repo / name, root)
    (root / 'shell.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Wayland
import "OverlayLogic.js" as Logic
ShellRoot {
  TimerOverlay { id: overlay }
  Timer {
    interval: 200; running: true
    onTriggered: {
      function check(value, message) { if (!value) throw new Error(message) }
      try {
        var state = {phase: "active", timer: "−00:01:01", session: null, predictedEndUtcMs: 1000, predictedStartUtcMs: 2000}
        var config = {overlayMode: "countdown"}
        check(!Logic.view(state, config).show, "61 seconds hidden")
        state.timer = "−00:01:00"
        check(Logic.view(state, config).show, "60 seconds visible")
        state.timer = "+00:00:00"
        check(Logic.view(state, config).show, "zero visible")
        state.timer = "+00:15:00"
        check(Logic.view(state, config).show, "overrun visible")
        state.timer = "--:--:--"
        check(!Logic.view(state, config).show, "learning has no final countdown")
        check(Logic.view(state, {overlayMode: "always"}).show, "always includes learning")
        check(!Logic.view(state, {}).show, "off by default")
        state.predictedEndUtcMs = null
        state.timer = "+00:15:00"
        check(!Logic.view(state, config).show, "learning elapsed time is not overrun")
        state.predictedEndUtcMs = 1000
        check(Logic.view(state, config).symbol === "E", "epoch symbol")
        state.phase = "off"
        state.timer = "−00:00:30"
        check(Logic.view(state, config).symbol === "O", "off-time symbol")
        state.session = {kind: "focus", timer: "−00:25:00", status: "active"}
        check(!Logic.view(state, config).show, "session takes priority over due epoch")
        state.session = {kind: "focus", timer: "−00:00:40", status: "paused"}
        check(Logic.view(state, config).paused && Logic.view(state, config).show, "paused countdown preserved")
        check(Logic.view(state, config).symbol === "A", "activity symbol")
        for (var kind of ["rest", "long_rest"]) {
          state.session = {kind: kind, timer: "−00:05:00", status: "active"}
          check(Logic.view(state, config).symbol === "R", "both rest symbols")
          check(!Logic.view(state, config).show, "next stage hides countdown")
        }
        check(Logic.lead({overlaySeconds: -1}) === 60, "invalid lead falls back")
        check(Logic.opacity({overlayOpacity: 7}) === 0.65, "invalid opacity falls back")
        state.session = null
        state.timer = "−00:01:30"
        check(Logic.view(state, {overlayMode: "countdown", overlaySeconds: 90}).show, "custom lead")
        overlay.config = {overlayMode: "always"}
        overlay.timerState = state
        overlay.operational = true
        check(overlay.showing, "operational window shows")
        check(overlay.mask.width === 0 && overlay.mask.height === 0 && overlay.mask.regions.length === 0, "empty input region")
        check(overlay.WlrLayershell.keyboardFocus === WlrKeyboardFocus.None, "no keyboard focus")
        check(overlay.exclusionMode === ExclusionMode.Ignore, "does not reserve screen space")
        overlay.operational = false
        check(!overlay.showing, "errors/loading hide overlay")
        console.log("OVERLAY_PASS")
      } catch (error) { console.error("OVERLAY_FAIL " + error) }
      Qt.quit()
    }
  }
}''')
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    if result.returncode or 'OVERLAY_PASS' not in result.stdout or 'OVERLAY_FAIL' in result.stdout:
        raise SystemExit(result.stdout)
    print('Overlay passed: countdown boundary, overrun, learning, session priority, pause, settings bounds, input region and focus.')
