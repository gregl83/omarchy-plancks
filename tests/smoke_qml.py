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
import qs.Commons
import "Plancks" as Plancks
import "Plancks/Graphics.js" as Graphics
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
  Process {
    id: seedSession
    property bool withRest: false
    command: ["python3", "-c", "import sys;sys.path.insert(0,sys.argv[1]);import plancks,sessions,uuid; s=plancks.Store(); state=s.recover(); now=plancks.clock();now['utcMs']-=61000;now['bootMs']-=61000; c=dict(sessions.DEFAULTS,preset='custom',focusMinutes=1,rounds=1,finalBreak=sys.argv[2]=='true');s.session_action('session_started',str(uuid.uuid4()),state['sequence'],state['generation'],config=c,now=now)", decodeURIComponent(Qt.resolvedUrl("Plancks").toString().replace(/^file:\/\//, "")), String(withRest)]
  }
  property int attempts: 0
  property bool preview: PREVIEW
  function check(condition, message) {
    if (!condition) { console.error("SMOKE_FAIL " + message); Qt.quit(); }
    return condition
  }
  function checkCoffeeRefill(cup) {
    var state = Plancks.EpochController.state
    var saved = {phase: state.phase, timer: state.timer, elapsed: state.elapsed,
                 predictedStartUtcMs: state.predictedStartUtcMs, predictedEndUtcMs: state.predictedEndUtcMs}
    try {
      state.phase = "off"
      state.predictedStartUtcMs = 1
      state.timer = "−01:00:00"
      state.elapsed = "00:00:00"
      if (!check(cup.predicted && cup.fill === 0, "off-time cup starts empty")) return false
      state.timer = "−00:45:00"
      state.elapsed = "00:15:00"
      if (!check(cup.fill === 0.25, "off-time cup fills one quarter")) return false
      state.timer = "−00:15:00"
      state.elapsed = "00:45:00"
      if (!check(cup.fill === 0.75, "off-time cup fills three quarters")) return false
      state.timer = "+00:00:00"
      state.elapsed = "01:00:00"
      if (!check(cup.fill === 1 && !cup.overtime, "off-time cup full at zero")) return false
      state.timer = "+00:05:00"
      state.elapsed = "01:05:00"
      if (!check(cup.fill === 1 && cup.overtime, "off-time cup stays full past the prediction")) return false
      state.phase = "active"
      state.predictedEndUtcMs = 1
      state.timer = "−00:45:00"
      state.elapsed = "00:15:00"
      return check(cup.fill === 0.75 && !cup.overtime, "active cup consumes the same fraction")
    } finally {
      for (var key in saved) state[key] = saved[key]
    }
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
      if (!test.check(test.attempts < 100, "helper timeout at step " + test.step + ": " + Plancks.EpochController.error)) return
      if (!test.ipcDone || !Plancks.EpochController.ready || Plancks.EpochController.busy) return
      if (test.step === 0) {
        if (!test.check(widget.epoch.phase === "off", "initial phase")) return
        Plancks.EpochController.busy = true
        if (!test.check(Plancks.EpochController.ipc.primaryAction() === "busy", "Primary IPC busy guard")) return
        if (!test.check(Plancks.EpochController.ipc.toggleEpoch() === "busy", "IPC busy guard")) return
        if (!test.check(Plancks.EpochController.ipc.toggleEpochSkip() === "busy", "skip IPC busy guard")) return
        Plancks.EpochController.busy = false
        Plancks.EpochController.ready = false
        if (!test.check(Plancks.EpochController.ipc.primaryAction() === "not-ready", "Primary IPC readiness guard")) return
        if (!test.check(Plancks.EpochController.ipc.toggleEpoch() === "not-ready", "IPC readiness guard")) return
        if (!test.check(Plancks.EpochController.ipc.toggleEpochSkip() === "not-ready", "skip IPC readiness guard")) return
        Plancks.EpochController.ready = true
        test.toggleViaIpc()
        test.step = 1
      } else if (test.step === 1) {
        if (!test.check(widget.epoch.phase === "active" && second.epoch.phase === "active", "shared active epoch")) return
        if (test.preview) widget.open()
        test.step = 2
      } else if (test.step === 2) {
        if (widget.epoch.timer.indexOf("+") !== 0) return
        if (test.preview) {
          var cup = resetTest.findChild(widget, "plancks_coffee")
          if (widget.epoch.timer === "+00:00:00") return
          if (!test.check(cup && cup.predicted && cup.overtime && cup.fill === 0,
                          "coffee cup stays empty past the prediction")) return
        }
        if (!test.check(widget.epoch.indicator === "●", "overrun keeps active phase")) return
        test.toggleViaIpc()
        test.step = 3
      } else if (test.step === 3) {
        if (!test.check(widget.epoch.phase === "off" && second.epoch.phase === "off", "shared end transition")) return
        if (test.preview) {
          var learningCup = resetTest.findChild(widget, "plancks_coffee")
          if (!test.check(learningCup && learningCup.learning && !learningCup.predicted
                          && learningCup.fill === 0,
                          "learning cup shows no predicted fill")) return
          if (!test.checkCoffeeRefill(learningCup)) return
        }
        if (!test.check(widget.epoch.workSampleCount === 1, "completed sample")) return
        second.bar = verticalBar
        if (!test.check(second.vertical && second.implicitHeight > 40, "vertical layout")) return
        ipcCall.command[ipcCall.command.length - 1] = "toggleEpochSkip"
        test.toggleViaIpc()
        test.step = 5
      } else if (test.step === 5) {
        if (!test.check(widget.epoch.phase === "active" && widget.epoch.gapSampleCount === 0, "skip start excludes gap")) return
        test.toggleViaIpc()
        test.step = 6
      } else if (test.step === 6) {
        if (!test.check(widget.epoch.phase === "off" && widget.epoch.workSampleCount === 1, "skip end preserves learned epoch")) return
        if (!test.preview) Plancks.EpochController.reset()
        test.step = 4
      } else {
        if (test.preview && !test.resetUiDone) return
        if (!test.check(widget.epoch.phase === "off" && second.epoch.sequence === 0, "shared reset")) return
        if (!test.check(widget.epoch.workSampleCount === 0 && widget.epoch.lastStartUtcMs === null, "reset clears history")) return
        widget.close()
        console.log("PLANCKS_SMOKE_PASS: two widgets, IPC start/end, IPC guards, skip start/end, overrun, vertical layout, history inclusion, pagination, reset")
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
    // Quickshell does not initialize QtTest's text logger. Surface failures
    // explicitly so the Python runner can report the failed UI assertion.
    function verify(condition, message) {
      if (!condition) { console.error("SMOKE_FAIL " + message); Qt.quit(); throw new Error(message) }
    }
    function compare(actual, expected, message) {
      verify(actual === expected, (message || "Compare") + ": " + actual + " !== " + expected)
    }
    function tryVerify(callback, timeout, message) {
      var deadline = Date.now() + (timeout || 5000)
      while (!callback() && Date.now() < deadline) wait(20)
      verify(callback(), message || "UI condition timed out")
    }
    function test_resetConfirmation() {
      var notificationState = {phase: "active", elapsed: "00:30:00", timer: "−00:30:00",
                               predictedEndUtcMs: 1, predictedStartUtcMs: 1}
      compare(Graphics.notificationImage("coffee", notificationState), "assets/notifications/coffee/active/fill-050.png")
      notificationState.phase = "off"
      compare(Graphics.notificationImage("starship", notificationState), "assets/notifications/starship/off-time/fill-050.png")
      notificationState.timer = "+00:01:00"
      compare(Graphics.notificationImage("starship", notificationState), "assets/notifications/starship/overtime/off-time.png")
      notificationState.predictedStartUtcMs = null
      compare(Graphics.notificationImage("starship", notificationState), "assets/notifications/starship/learning/off-time.png")
      try { runConfirmation() }
      catch (error) { console.error("SMOKE_FAIL UI: " + error); Qt.quit(); throw error }
    }
    function runConfirmation() {
      var widgetButton = findChild(widget, "plancks_widgetButton")
      verify(widgetButton !== null, "Find the bar button")
      for (var fraction of [0.05, 0.25, 0.5, 0.75, 0.95]) {
        mouseMove(widget, widget.width + 10, widget.height / 2)
        wait(20)
        mouseMove(widget, widget.width * fraction, widget.height / 2)
        tryVerify(function() { return widgetButton.tooltipHovered }, 1000,
                  "Tooltip hover covers the whole timer at " + fraction)
      }
      widget.open()
      wait(100)
      var panel = findChild(widget, "plancks_root")
      verify(panel !== null, "Find the production panel")
      var keys = findChild(panel, "plancks_keys")
      verify(keys !== null)
      // QtTest sends keys to its containing window: use the actual popup.
      parent = keys
      var scroll = findChild(panel, "plancks_scroll")
      function findVisual(item, name) {
        if (item.objectName === name) return item
        for (var child of item.children || []) {
          var found = findVisual(child, name)
          if (found) return found
        }
        return null
      }
      var predictions = findVisual(scroll.contentItem, "plancks_Predictions_details")
      var history = findVisual(scroll.contentItem, "plancks_History_details")
      verify(predictions !== null && history !== null)
      compare(predictions.columns, 4, "Two prediction pairs per row at the normal panel width")
      compare(history.columns, 4, "Two history pairs per row at the normal panel width")
      compare(predictions.width, history.width, "Both sections use the same column widths")
      var action = findChild(panel, "plancks_actionButton")
      var skip = findChild(panel, "plancks_skipButton")
      verify(skip !== null)
      compare(skip.text, "Skip to start epoch")
      verify(skip.x > action.x, "Skip is to the right")
      compare(skip.y, action.y)
      compare(skip.width, action.width, "Epoch buttons have equal width")
      verify(action.width >= action.implicitWidth, "Primary label fits")
      verify(skip.width >= skip.implicitWidth, "Skip label fits")
      // Preserve the epoch-only contract before introducing child sessions.
      var baselineSequence = Plancks.EpochController.state.sequence
      var baselinePhase = Plancks.EpochController.state.phase
      var pageTitle = findChild(panel, "plancks_pageTitle")
      var header = pageTitle.parent.parent
      var headerHeight = header.height
      var headerWidth = header.width
      var settingsNav = findChild(panel, "plancks_settingsButton")
      var settingsX = settingsNav.x
      for (var destination of ["settings", "history"]) {
        if (destination === "settings") panel.openSettings(); else panel.openHistory()
        wait(100)
        compare(header.height, headerHeight, "Header height remains stable in " + destination)
        compare(header.width, headerWidth, "Header width remains stable in " + destination)
        compare(pageTitle.text, destination === "settings" ? "Settings" : "History")
        keys.forceActiveFocus()
        keyClick(Qt.Key_Escape)
        verify(panel.opened && !panel.showingSettings && !panel.showingHistory,
               "Subview Escape returns to main without closing")
        compare(settingsNav.x, settingsX, "Settings position remains stable")
      }
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      var savedReady = Plancks.EpochController.ready
      Plancks.EpochController.busy = true
      verify(!action.enabled && !skip.enabled, "Pending writes disable epoch actions")
      Plancks.EpochController.busy = false
      Plancks.EpochController.ready = false
      verify(!action.enabled && !skip.enabled, "Unavailable storage disables epoch actions")
      Plancks.EpochController.error = "Regression test storage error"
      verify(!widgetButton.dimmed, "Storage errors remain undimmed during off-time")
      compare(widgetButton.tooltipText, "Regression test storage error", "Storage error is the bar tooltip")
      var retry = findChild(panel, "plancks_retryButton")
      verify(retry && retry.visible && retry.enabled, "Storage failure exposes Retry")
      Plancks.EpochController.error = ""
      Plancks.EpochController.ready = savedReady
      compare(Plancks.EpochController.state.sequence, baselineSequence, "Navigation and guards do not write history")
      compare(Plancks.EpochController.state.phase, baselinePhase)
      keys.forceActiveFocus()
      keyClick(Qt.Key_Escape)
      verify(!panel.opened, "Escape on main closes the panel")
      widget.open()
      wait(100)
      compare(Plancks.EpochController.state.sequence, baselineSequence, "Close/reopen does not change epochs")
      verify(action.Accessible.name.length > 0 && widgetButton.Accessible.name.length > 0,
             "Main actions and bar remain accessible")
      var reset = findChild(panel, "plancks_resetButton")
      var cancel = findChild(panel, "plancks_cancelButton")
      var confirm = findChild(panel, "plancks_confirmButton")
      var warning = findChild(panel, "plancks_resetWarning")
      var settingsButton = findChild(panel, "plancks_settingsButton")
      var settingsView = findChild(panel, "plancks_settingsView")
      verify(settingsButton.visible && !reset.visible, "Main navigation exposes Settings; reset stays in Settings")
      // The bar can inject saved preferences after constructing a widget.
      widget.settings = Object.assign({}, widget.settings, {animatedGraphic: "starship"})
      settingsButton.forceActiveFocus()
      keyClick(Qt.Key_Return)
      verify(panel.showingSettings && settingsView.visible && !action.visible, "Settings replaces main content")
      var graphicChoice = findVisual(scroll.contentItem, "plancks_graphic_coffee")
      var graphicPreview = findVisual(scroll.contentItem, "plancks_graphicPreview_coffee")
      var initialStarship = findVisual(scroll.contentItem, "plancks_graphic_starship")
      verify(initialStarship.selected && !graphicChoice.selected && graphicPreview.running,
             "Saved Starship selection is present when Settings first opens")
      compare(initialStarship.color.toString(), Style.selectedFillFor(initialStarship.foreground, initialStarship.accent).toString(),
              "Saved selection is painted immediately on first open")
      var initialDrawing = findVisual(scroll.contentItem, "plancks_graphicPreview_starship")
      verify(initialDrawing.item && initialDrawing.item.objectName === "plancks_starshipDrawing",
             "Starship preview loads the correct drawing on first open")
      var graphicSequence = Plancks.EpochController.state.sequence
      graphicChoice.forceActiveFocus()
      keyClick(Qt.Key_Return)
      compare(widget.settings.animatedGraphic, "coffee", "Graphic choice is saved in widget settings")
      compare(widget.animatedGraphic, "coffee")
      compare(Plancks.EpochController.state.sequence, graphicSequence, "Choosing a graphic does not change epochs")
      var starshipChoice = findVisual(scroll.contentItem, "plancks_graphic_starship")
      var starshipPreview = findVisual(scroll.contentItem, "plancks_graphicPreview_starship")
      compare(starshipChoice.y, graphicChoice.y, "Both graphics occupy the same row")
      verify(starshipChoice.x > graphicChoice.x, "Starship is the second tile")
      starshipChoice.forceActiveFocus()
      keyClick(Qt.Key_Return)
      verify(starshipChoice.selected && !graphicChoice.selected, "Only Starship is selected")
      wait(160)
      var selectionColor = starshipChoice.color.toString()
      compare(selectionColor, Style.selectedFillFor(starshipChoice.foreground, starshipChoice.accent).toString(),
              "Selected tile retains its selection fill while focused")
      keys.forceActiveFocus()
      wait(160)
      compare(starshipChoice.color.toString(), selectionColor, "Selection styling stays the same after focus leaves")
      compare(widget.settings.animatedGraphic, "starship", "Starship selection is saved")
      var timerGraphic = findVisual(scroll.contentItem, "plancks_timerGraphic")
      tryVerify(function() { return timerGraphic.item && timerGraphic.item.objectName === "plancks_starshipDrawing" })
      compare(Plancks.EpochController.state.sequence, graphicSequence, "Graphic selection leaves epoch state intact")
      for (var frame of [
        {elapsed: 0, fill: 0, learning: false, opacity: 0.45},
        {elapsed: 1600, fill: 0, learning: true, opacity: 1},
        {elapsed: 4000, fill: 1, learning: false, opacity: 1},
        {elapsed: 5800, fill: 0.5, learning: false, opacity: 1},
        {elapsed: 7600, fill: 0, learning: false, opacity: 1},
        {elapsed: 9200, fill: 0, learning: true, opacity: 0.45},
        {elapsed: 13400, fill: 0.5, learning: false, opacity: 0.45},
        {elapsed: 15200, fill: 1, learning: false, opacity: 0.45}
      ]) {
        settingsView.previewElapsed = frame.elapsed
        compare(graphicPreview.fill, frame.fill, "Preview fill at " + frame.elapsed)
        compare(graphicPreview.learning, frame.learning)
        compare(graphicPreview.opacity, frame.opacity)
        compare(starshipPreview.fill, graphicPreview.fill, "Both previews share the fuel level")
        compare(starshipPreview.learning, graphicPreview.learning)
        compare(starshipPreview.elapsed, graphicPreview.elapsed)
        compare(starshipPreview.item.flameVisible, starshipPreview.phase === "active" && !starshipPreview.overtime, "Flame stops past the expected epoch end")
        compare(starshipPreview.item.padVisible, starshipPreview.phase === "off", "Pad identifies off-time")
        compare(starshipPreview.item.fuelConnectionVisible, starshipPreview.phase === "off", "Fuel connection stays visible throughout off-time")
        compare(starshipPreview.item.overtime, starshipPreview.overtime)
      }
      var tooltipSwitch = findChild(panel, "plancks_tooltipsSwitch")
      verify(tooltipSwitch !== null && tooltipSwitch.checked, "Tooltips default to enabled")
      var tooltipSequence = Plancks.EpochController.state.sequence
      tooltipSwitch.forceActiveFocus()
      keyClick(Qt.Key_Space)
      verify(!tooltipSwitch.checked && !panel.tooltipsEnabled && !widget.tooltipsEnabled,
             "Keyboard toggle disables tooltips")
      compare(widget.settings.tooltipsEnabled, false, "Preference is stored in widget settings")
      compare(widgetButton.tooltipText, "", "Bar tooltip is disabled")
      compare(action.tooltipText, "", "Panel button tooltip is disabled")
      verify(action.Accessible.description.length > 0, "Accessible action description is retained")
      keyClick(Qt.Key_Tab)
      verify(graphicChoice.activeFocus, "Tab moves from tooltips to graphics")
      keyClick(Qt.Key_Tab)
      verify(starshipChoice.activeFocus, "Tab reaches the second graphic")
      keyClick(Qt.Key_Tab)
      var insightToggle = findChild(panel, "plancks_insightsToggle")
      var finishToggle = findChild(panel, "plancks_finishNotificationsToggle")
      var insightPreview = findChild(panel, "plancks_previewInsightButton")
      var warningMinutes = findChild(panel, "plancks_finishWarningMinutes")
      verify(insightToggle.activeFocus && !insightToggle.checked, "Insights start disabled")
      keyClick(Qt.Key_Space)
      verify(widget.insightsEnabled && insightToggle.checked, "Insights preference is stored")
      keyClick(Qt.Key_Tab)
      var cadence = findChild(panel, "plancks_insightFrequency")
      verify(cadence.activeFocus, "Enabled cadence receives focus")
      keyClick(Qt.Key_Tab)
      verify(insightPreview.activeFocus, "Preview follows occasional insight controls")
      keyClick(Qt.Key_Return)
      tryVerify(function() { return Plancks.EpochController.notificationMessage.length > 0 }, 3000)
      compare(Plancks.EpochController.notificationImage,
              decodeURIComponent(Qt.resolvedUrl("Plancks/" + Graphics.notificationImage(Plancks.EpochController.settings.animatedGraphic, Plancks.EpochController.state)).toString().replace(/^file:\/\//, "")),
              "Notification captures the selected graphic and current state")
      compare(Plancks.EpochController.state.sequence, tooltipSequence, "Preview does not change epoch history")
      keyClick(Qt.Key_Tab)
      verify(finishToggle.activeFocus && !finishToggle.checked, "Finish notifications are independent")
      keyClick(Qt.Key_Space)
      verify(widget.finishNotificationsEnabled, "Finish notifications can be enabled")
      keyClick(Qt.Key_Tab)
      verify(warningMinutes.activeFocus, "Warning minutes are editable")
      verify(!warningMinutes.readOnly && warningMinutes.cursorVisible, "Native editing and caret remain enabled")
      warningMinutes.text = "1"
      warningMinutes.selectAll()
      keyClick(Qt.Key_2)
      compare(warningMinutes.text, "2", "Typing replaces selected text")
      keyClick(Qt.Key_Z, Qt.ControlModifier)
      compare(warningMinutes.text, "1", "Native undo works")
      warningMinutes.selectAll()
      keyClick(Qt.Key_V, Qt.ControlModifier)
      tryCompare(warningMinutes, "text", "20, 1")
      warningMinutes.text = "1"
      warningMinutes.selectAll()
      keyClick(Qt.Key_Insert, Qt.ShiftModifier)
      tryCompare(warningMinutes, "text", "20, 1")
      warningMinutes.text = ""
      keyClick(Qt.Key_Paste)
      tryCompare(warningMinutes, "text", "20, 1")
      warningMinutes.text = ""
      mouseClick(warningMinutes, warningMinutes.width / 2, warningMinutes.height / 2, Qt.MiddleButton)
      tryCompare(warningMinutes, "text", "20, 1")
      warningMinutes.text = "1".repeat(80)
      warningMinutes.cursorPosition = 80
      keyClick(Qt.Key_2)
      compare(warningMinutes.length, 80, "Typing respects the character limit")
      warningMinutes.text = "20, 1"
      keyClick(Qt.Key_Return)
      compare(widget.finishWarningSeconds.join(","), "1200,60", "Warning minutes are saved as seconds")
      warningMinutes.text = "invalid"
      keyClick(Qt.Key_Return)
      compare(widget.finishWarningSeconds.join(","), "1200,60", "Invalid warning values preserve preferences")
      warningMinutes.text = "30, 1"
      keyClick(Qt.Key_Return)
      keyClick(Qt.Key_Tab)
      insightToggle.forceActiveFocus()
      keyClick(Qt.Key_Space)
      finishToggle.forceActiveFocus()
      keyClick(Qt.Key_Space)
      verify(!widget.insightsEnabled && !widget.finishNotificationsEnabled, "Both options can be disabled")
      finishToggle.forceActiveFocus()
      keyClick(Qt.Key_Tab)
      verify(reset.activeFocus, "Tab moves from finish notifications to reset")
      keyClick(Qt.Key_Backtab)
      verify(finishToggle.activeFocus, "Disabled warning field is skipped")
      keyClick(Qt.Key_Backtab)
      verify(insightPreview.activeFocus, "Preview belongs to occasional insights")
      keyClick(Qt.Key_Backtab)
      verify(insightToggle.activeFocus, "Disabled cadence is skipped")
      keyClick(Qt.Key_Backtab)
      verify(starshipChoice.activeFocus, "Shift-Tab moves from insights to graphics")
      keyClick(Qt.Key_Backtab)
      verify(graphicChoice.activeFocus, "Shift-Tab reaches the first graphic")
      keyClick(Qt.Key_Backtab)
      verify(tooltipSwitch.activeFocus, "Shift-Tab moves from graphics to tooltips")
      tooltipSwitch.forceActiveFocus()
      keyClick(Qt.Key_Space)
      verify(tooltipSwitch.checked && panel.tooltipsEnabled, "Tooltips can be enabled again")
      compare(Plancks.EpochController.state.sequence, tooltipSequence, "Tooltip preference does not change epochs")
      keyClick(Qt.Key_Escape)
      verify(!panel.showingSettings && keys.activeFocus, "Escape returns focus to the panel without a persistent gear outline")
      verify(!graphicPreview.running && graphicPreview.elapsed === 0, "Preview stops and resets outside Settings")
      wait(300)
      keys.forceActiveFocus()
      keyClick(Qt.Key_Tab)
      verify(action.activeFocus, "Tab reaches epoch action")
      keyClick(Qt.Key_Tab)
      verify(skip.activeFocus, "Tab reaches skip action")
      keyClick(Qt.Key_Tab)
      var historyButton = panel.historyLink
      verify(historyButton.activeFocus, "Tab reaches history")
      keyClick(Qt.Key_Return)
      verify(panel.showingHistory, "History replaces the main panel")
      var historyView = findChild(panel, "plancks_historyView")
      var search = findChild(panel, "plancks_historySearch")
      search.forceActiveFocus()
      keyClick(Qt.Key_V, Qt.ControlModifier)
      tryCompare(search, "text", "20, 1")
      search.text = ""
      verify(historyView.visible)
      var back = findChild(panel, "plancks_historyBackButton")
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.total, 3, "Three completed intervals before paging")
      var epochsTab = findChild(panel, "plancks_epochsTab")
      var sessionsTab = findChild(panel, "plancks_sessionsTab")
      var tabX = sessionsTab.x
      var tabWidth = sessionsTab.width
      function steadyHover(button) {
        button.focus = false
        mouseMove(button, -20, -20)
        wait(150)
        var idleFill = String(button.color)
        var idleBorder = JSON.stringify(button.borderSpec)
        mouseMove(button, button.width / 2, button.height / 2)
        wait(250)
        verify(button.hot, "Pointer activates tab hover")
        var fill = String(button.color)
        var border = JSON.stringify(button.borderSpec)
        if (button.selected) {
          compare(fill, idleFill, "Selected tab fill does not change on hover")
          compare(border, idleBorder, "Selected tab border does not change on hover")
        }
        for (var i = 0; i < 12; i++) {
          mouseMove(button, button.width / 2 + i % 3, button.height / 2)
          wait(40)
          verify(button.hot, "Hover stays active while moving within the tab")
          compare(String(button.color), fill, "Tab hover fill stays steady")
          compare(JSON.stringify(button.borderSpec), border, "Tab hover border stays steady")
        }
      }
      steadyHover(epochsTab)
      steadyHover(sessionsTab)
      mouseClick(sessionsTab, sessionsTab.width / 2, sessionsTab.height / 2)
      tryVerify(function() { return panel.sessionHistoryMode && !Plancks.EpochController.sessionHistoryLoading })
      steadyHover(sessionsTab)
      compare(sessionsTab.x, tabX, "Selecting a tab preserves its hit target")
      compare(sessionsTab.width, tabWidth)
      mouseClick(epochsTab, epochsTab.width / 2, epochsTab.height / 2)
      tryVerify(function() { return !panel.sessionHistoryMode && !Plancks.EpochController.historyLoading })
      steadyHover(epochsTab)
      mouseMove(epochsTab, -20, -20)

      var epochTrend = findVisual(scroll.contentItem, "plancks_epochTrend")
      var offTrend = findVisual(scroll.contentItem, "plancks_offTrend")
      verify(epochTrend.visible && offTrend.visible, "Both completed interval types have a trend")
      compare(epochTrend.points.length, 2)
      compare(offTrend.points.length, 1)
      var skipped = findVisual(scroll.contentItem, "plancks_historyToggle_0")
      verify(skipped !== null && !skipped.checked, "Skipped interval is unchecked")
      skipped.forceActiveFocus()
      keyClick(Qt.Key_Space)
      tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.historyLoading
        && Plancks.EpochController.state.workSampleCount === 2 })
      skipped = findVisual(scroll.contentItem, "plancks_historyToggle_0")
      verify(skipped.checked, "Included interval is checked after saving")
      skipped.forceActiveFocus()
      keyClick(Qt.Key_Space)
      tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.historyLoading
        && Plancks.EpochController.state.workSampleCount === 1 })
      // Produce enough skipped intervals to exercise three pages without
      // changing the learned samples used by the reset checks below.
      for (var i = 0; i < 12; i++) {
        tryVerify(function() { return Plancks.EpochController.ready && !Plancks.EpochController.busy })
        var beforeSequence = Plancks.EpochController.state.sequence
        Plancks.EpochController.transition(true)
        tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.historyLoading
          && Plancks.EpochController.state.sequence === beforeSequence + 1 })
      }
      Plancks.EpochController.requestHistory(0)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.pages, 3, "Three history pages after adding intervals")
      compare(Plancks.EpochController.history.rows.length, 5)
      var next = findChild(panel, "plancks_historyNextButton")
      var previous = findChild(panel, "plancks_historyPreviousButton")
      verify(next.enabled && !previous.enabled)
      next.forceActiveFocus()
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.page, 1)
      compare(Plancks.EpochController.history.rows.length, 5)
      verify(previous.enabled && next.enabled)
      next.forceActiveFocus()
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.page, 2)
      compare(Plancks.EpochController.history.rows.length, 5)
      compare(epochTrend.points.length, 8, "Trend stays independent of the page")
      compare(offTrend.points.length, 7, "Off-time trend stays independent of the page")
      verify(previous.enabled && !next.enabled)
      previous.forceActiveFocus()
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.page, 1)
      previous.forceActiveFocus()
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.page, 0)
      // Search all pages, preserve input focus, and keep trends independent.
      var search = findChild(panel, "plancks_historySearch")
      var clearSearch = findChild(panel, "plancks_historyClearSearch")
      search.forceActiveFocus()
      keyClick(Qt.Key_O)
      keyClick(Qt.Key_C)
      keyClick(Qt.Key_T)
      keyClick(Qt.Key_Space)
      wait(500)
      compare(search.text, "oct ", "Search preserves a trailing space across the debounce")
      compare(search.cursorPosition, 4, "Search does not move the cursor after a request")
      keyClick(Qt.Key_2)
      tryVerify(function() { return !Plancks.EpochController.historyLoading && Plancks.EpochController.history.query === "oct 2" })
      compare(search.text, "oct 2", "Typing a date preserves its space")
      search.text = "epoch"
      tryVerify(function() { return !Plancks.EpochController.historyLoading && Plancks.EpochController.history.query === "epoch" })
      compare(Plancks.EpochController.history.total, 8)
      compare(Plancks.EpochController.history.pages, 2)
      verify(search.activeFocus, "Searching preserves text input focus")
      var searchSequence = Plancks.EpochController.state.sequence
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.state.sequence, searchSequence, "Enter in search does not change phase")
      next.forceActiveFocus()
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.page, 1)
      compare(Plancks.EpochController.history.rows.length, 3)
      verify(Plancks.EpochController.history.rows.every(function(row) { return row.kind === "epoch" }))
      search.forceActiveFocus()
      search.text = "no matching intervals"
      tryVerify(function() { return !Plancks.EpochController.historyLoading && Plancks.EpochController.history.query === search.text })
      compare(Plancks.EpochController.history.total, 0)
      compare(Plancks.EpochController.history.page, 0)
      compare(epochTrend.points.length, 8)
      compare(offTrend.points.length, 7)
      clearSearch.forceActiveFocus()
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.historyLoading && Plancks.EpochController.history.query === "" })
      compare(Plancks.EpochController.history.total, 15)
      verify(search.activeFocus, "Clear returns focus to search")
      // Escape also clears text that is still waiting for the search debounce.
      search.text = "epoch"
      keyClick(Qt.Key_Escape)
      compare(search.text, "")
      verify(search.activeFocus && panel.showingHistory, "Escape clears search and keeps input focus")
      tryVerify(function() { return !Plancks.EpochController.historyLoading && Plancks.EpochController.history.query === "" })
      compare(Plancks.EpochController.history.total, 15)
      wait(350)
      compare(Plancks.EpochController.historyQuery, "", "Escape cancels the pending search")
      keyClick(Qt.Key_Escape)
      verify(!panel.showingHistory && panel.opened, "Escape in an empty search returns to the main panel")
      tryVerify(function() { return keys.activeFocus })
      settingsButton.forceActiveFocus()
      keyClick(Qt.Key_Return)
      verify(panel.showingSettings && reset.visible, "Reset is available through Settings")
      reset.forceActiveFocus()
      verify(reset.activeFocus, "Reset receives keyboard focus")
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
      verify(!action.visible && !skip.visible && !predictions.visible && !history.visible,
             "Confirmation replaces the normal content")
      compare(cancel.width, confirm.width, "Reset actions have equal widths")
      compare(cancel.y, confirm.y, "Reset actions share one row")
      verify(confirm.x > cancel.x, "Delete is to the right of Cancel")
      verify(cancel.width >= cancel.implicitWidth && confirm.width >= confirm.implicitWidth,
             "Reset action labels fit")
      unchanged()
      keyClick(Qt.Key_Return)
      verify(!panel.confirmingReset && panel.showingSettings, "Activating Cancel returns to Settings")
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
      panel.openHistory()
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      verify(!epochTrend.visible && !offTrend.visible, "No charts when history is empty")
      back.forceActiveFocus()
      keyClick(Qt.Key_Escape)
      console.log("PLANCKS_RESET_UI_PASS")
      // Exercise the new session flows only after the unchanged epoch UX suite.
      panel.closeSettings()
      panel.closeHistory()
      var configure = findChild(panel, "plancks_configureSession")
      verify(!configure.enabled, "Off-time prevents session configuration")
      Plancks.EpochController.transition()
      tryVerify(function() { return Plancks.EpochController.ready && !Plancks.EpochController.busy && widget.epoch.phase === "active" })
      configure.forceActiveFocus()
      keyClick(Qt.Key_Return)
      verify(panel.showingSession, "Configure session opens its page")
      var config = findChild(panel, "plancks_sessionConfig")
      compare(findChild(panel, "plancks_pageTitle").text, "Session")
      compare(config.draft.preset, "pomodoro")
      compare(config.summary.minutes, 130, "Pomodoro includes its final long break")
      var draftSequence = widget.epoch.sequence
      config.edit("finalBreak", false)
      compare(config.draft.preset, "custom")
      compare(config.summary.minutes, 115)
      var numericKeys = ["focusMinutes", "shortBreakMinutes", "rounds", "longBreakMinutes", "longBreakEvery"]
      for (var numericKey of numericKeys) {
        var numericField = findVisual(config, "plancks_session_" + numericKey)
        verify(typeof numericField.boundedPaste === "function", numericKey + " uses bounded clipboard input")
        numericField.forceActiveFocus()
        keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_Backspace)
        keyClick(Qt.Key_1)
        compare(config.draft[numericKey], 1, numericKey + " updates from typing")
      }
      config.load(null)
      compare(config.draft.preset, "pomodoro", "Programmatic field refresh preserves preset identity")
      var focusMinutes = findVisual(config, "plancks_session_focusMinutes")
      focusMinutes.forceActiveFocus()
      keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_Backspace)
      compare(focusMinutes.text, "", "Editing preserves an empty numeric field")
      verify(config.validation.length > 0 && !findChild(config, "plancks_startSession").enabled, "Invalid draft cannot start")
      keyClick(Qt.Key_1)
      compare(focusMinutes.text, "1", "Typing a duration preserves the entered value")
      compare(config.draft.focusMinutes, 1)
      focusMinutes.selectAll()
      keyClick(Qt.Key_V, Qt.ControlModifier)
      tryCompare(focusMinutes, "text", "20,", 3000)
      verify(config.validation.length > 0 && !findChild(config, "plancks_startSession").enabled,
             "Bounded paste of invalid numeric text cannot start a session")
      focusMinutes.selectAll()
      keyClick(Qt.Key_1); keyClick(Qt.Key_8); keyClick(Qt.Key_0); keyClick(Qt.Key_9)
      compare(focusMinutes.text, "180", "Numeric input is limited to three characters")
      compare(config.draft.focusMinutes, 180)
      config.load(null)
      compare(focusMinutes.text, "25", "Restoring the preset refreshes numeric fields")
      keys.forceActiveFocus(); keyClick(Qt.Key_Escape)
      verify(!panel.showingSession && panel.opened)
      compare(widget.epoch.sequence, draftSequence, "Draft cancel writes no timer event")
      configure.forceActiveFocus(); keyClick(Qt.Key_Return)
      config.edit("rounds", 1); config.edit("finalBreak", false); config.edit("focusMinutes", 1)
      var sessionName = findVisual(config, "plancks_sessionName")
      verify(sessionName.visible)
      sessionName.forceActiveFocus()
      keyClick(Qt.Key_R); keyClick(Qt.Key_E); keyClick(Qt.Key_A); keyClick(Qt.Key_D)
      compare(config.draft.name, "read")

      var startSession = findChild(config, "plancks_startSession")
      startSession.forceActiveFocus(); keyClick(Qt.Key_Return)
      tryVerify(function() { return !!widget.epoch.session && !Plancks.EpochController.busy && !panel.showingSession })
      compare(widget.settings.sessionConfig.rounds, 1, "Successful configuration is remembered")
      compare(widget.settings.sessionConfig.name, "read", "Custom name is saved in settings")
      compare(widget.epoch.session.name, "read", "Custom name is saved in the running session")
      verify(findChild(panel, "plancks_sessionTimer").text.indexOf("<sub>A</sub>") >= 0)

      compare(widget.epoch.session.sessionId, second.epoch.session.sessionId, "Widgets share a single session")
      verify(widgetButton.Accessible.name.indexOf("Activity") >= 0, "Bar identifies session activity")
      verify(!findChild(panel, "plancks_advanceSession").visible, "Advance action hidden before target")
      verify(!findChild(panel, "plancks_advanceSession").enabled, "Early advancement disabled")
      var earlySequence = widget.epoch.sequence
      widget.close()
      compare(Plancks.EpochController.ipc.primaryAction(), "controls-opened")
      tryVerify(function() { return panel.opened && findChild(panel, "plancks_pauseSession").activeFocus })
      compare(widget.epoch.sequence, earlySequence, "Early primary action does not change timers")
      compare(Plancks.EpochController.primaryActionLabel, "Open session controls")
      verify(widgetButton.tooltipText.indexOf("Primary action: Open session controls") >= 0)
      wait(650)
      var runningBarWidth = widget.implicitWidth
      var pause = findChild(panel, "plancks_pauseSession")
      compare(pause.text, "Pause")
      verify(pause.tooltipText.indexOf("keep the epoch running") >= 0)
      var progress = findChild(panel, "plancks_sessionProgress")
      var progressTip = findChild(panel, "plancks_sessionProgressTip")
      panel.revealButton(progress)
      wait(100)
      mouseMove(progress, progress.width / 2, progress.height / 2)
      tryVerify(function() { return progressTip.visible })
      verify(progressTip.text.indexOf("Current stage:") === 0)
      widget.setTooltipsEnabled(false)
      tryVerify(function() { return !progressTip.visible })
      compare(pause.tooltipText, "")
      compare(startSession.tooltipText, "")
      widget.setTooltipsEnabled(true)
      mouseMove(progress, -20, -20)
      wait(100)
      var pauseSlotY = pause.y
      var stopSlotY = findChild(panel, "plancks_stopSession").y
      pause.forceActiveFocus(); keyClick(Qt.Key_Return)
      tryVerify(function() { return widget.epoch.session.status === "paused" && !Plancks.EpochController.busy })
      compare(widget.implicitWidth, runningBarWidth, "Pause marker does not resize the bar")
      var frozen = widget.epoch.session.timer
      wait(1100)
      compare(widget.epoch.session.timer, frozen, "Paused time stays frozen")
      widget.close()
      compare(Plancks.EpochController.ipc.primaryAction(), "controls-opened")
      tryVerify(function() { return panel.opened && pause.activeFocus })
      compare(widget.epoch.session.status, "paused", "Primary action never resumes a paused session")
      wait(650)
      pause.forceActiveFocus(); keyClick(Qt.Key_Return)
      tryVerify(function() { return widget.epoch.session.status === "running" && !Plancks.EpochController.busy })
      console.log("SESSION_UI_PAUSE_OK")
      var pausedSequence = widget.epoch.sequence
      widget.close()
      compare(Plancks.EpochController.ipc.toggleEpochSkip(), "confirmation-pending", "Quick-key requests confirmation")
      tryVerify(function() { return panel.opened && panel.confirmingEpochEnd })
      var endCancel = findChild(panel, "plancks_cancelEpochEnd")
      var endConfirm = findChild(panel, "plancks_confirmEpochEnd")
      tryVerify(function() { return endCancel.activeFocus })
      compare(Plancks.EpochController.ipc.toggleEpochSkip(), "confirmation-pending")
      compare(Plancks.EpochController.ipc.primaryAction(), "confirmation-pending", "Primary action cannot bypass epoch confirmation")
      compare(widget.epoch.sequence, pausedSequence, "Repeated shortcut cannot close session")
      keyClick(Qt.Key_Escape)
      verify(!panel.confirmingEpochEnd && widget.epoch.session, "Escape preserves session")
      compare(Plancks.EpochController.ipc.toggleEpochSkip(), "confirmation-pending")
      tryVerify(function() { return endCancel.activeFocus })
      keyClick(Qt.Key_Tab); verify(endConfirm.activeFocus)
      keyClick(Qt.Key_Return)
      tryVerify(function() { return widget.epoch.phase === "off" && !widget.epoch.session && !Plancks.EpochController.busy })
      compare(widget.epoch.sequence, pausedSequence + 1, "Cascade closes both in one event")
      compare(widget.epoch.workSampleCount, 0, "Skip intent survives confirmation")
      console.log("SESSION_UI_CASCADE_OK")
      panel.openHistory()
      panel.sessionHistoryMode = true
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.rows.length === 1 })
      var sessionHistory = findChild(panel, "plancks_sessionHistory")
      var sessionSearch = findVisual(sessionHistory, "plancks_sessionSearch")
      verify(typeof sessionSearch.boundedPaste === "function", "Session search uses the released bounded field")
      sessionSearch.forceActiveFocus(); keyClick(Qt.Key_V, Qt.ControlModifier)
      tryCompare(sessionSearch, "text", "20, 1")
      var clearSessionSearch = findVisual(sessionHistory, "plancks_sessionsClearSearch")
      verify(clearSessionSearch.visible)
      clearSessionSearch.forceActiveFocus(); keyClick(Qt.Key_Return)
      compare(sessionSearch.text, "")
      verify(sessionSearch.activeFocus, "Clearing session search returns focus to the field")
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.rows.length === 1 })
      sessionSearch.text = "custom"
      keyClick(Qt.Key_Return)
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.query === "custom" })
      compare(findVisual(sessionHistory, "plancks_sessionsSearchCount").text, "1 matching session")
      widget.close()
      wait(200)
      widget.open(); panel.openHistory()
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading })
      compare(sessionSearch.text, "custom", "Reopening preserves the session query like epoch history")
      sessionSearch.forceActiveFocus(); keyClick(Qt.Key_Escape)
      compare(sessionSearch.text, "")
      verify(panel.showingHistory, "Escape clears session search before leaving history")
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.query === "" })

      var focusTrend = findVisual(sessionHistory, "plancks_sessionFocusTrend")
      verify(focusTrend.visible && focusTrend.sessionTrend)
      compare(focusTrend.points.length, 1)
      verify(focusTrend.points[0].stopped)
      var activityGrid = findVisual(sessionHistory, "plancks_sessionActivity")
      verify(activityGrid.visible)
      compare(activityGrid.width, focusTrend.width)
      verify(activityGrid.x > focusTrend.x)
      verify(activityGrid.weeks > 1 && activityGrid.weeks <= 26)
      compare(activityGrid.cells.length, activityGrid.weeks * 7)
      verify(Math.abs(activityGrid.gridWidth - activityGrid.width) < 0.01)
      compare(focusTrend.plotHeight, activityGrid.gridHeight)
      verify(activityGrid.cells.some(function(cell) { return cell.durationMs > 0 }))
      activityGrid.activity = {today: "2026-03-01", days: {"2026-02-28": {durationMs: 60000, sessions: 1}}}
      compare(activityGrid.cells[activityGrid.cells.length - 1].date.getDay(), 0)
      compare(activityGrid.cells.filter(function(cell) { return cell.durationMs > 0 }).length, 1)
      activityGrid.activity = Qt.binding(function() { return sessionHistory.history.activity || ({}) })

      compare(Plancks.EpochController.sessionHistory.rows[0].status, "stopped")
      compare(Plancks.EpochController.sessionHistory.rows[0].config.name, "read")
      var sessionPrevious = findVisual(sessionHistory, "plancks_sessionsPrevious")
      var sessionNext = findVisual(sessionHistory, "plancks_sessionsNext")
      var sessionPage = findVisual(sessionHistory, "plancks_sessionsPageLabel")
      compare(sessionPage.text, "Page 1 of 1")
      compare(sessionPrevious.width, sessionNext.width)
      compare(sessionPrevious.x, 0)
      compare(sessionNext.x + sessionNext.width, sessionNext.parent.width)
      verify(!sessionPrevious.enabled && !sessionNext.enabled)
      verify(!sessionPrevious.focusable && !sessionNext.focusable)
      compare(sessionPrevious.opacity, 0.35)
      compare(sessionNext.opacity, 0.35)
      var sessionToggle = findVisual(sessionHistory, "plancks_sessionToggle_0")
      verify(sessionToggle.checked)
      sessionToggle.forceActiveFocus(); keyClick(Qt.Key_Space)
      tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.rows[0].excludedFromStatistics === true })
      verify(Plancks.EpochController.sessionHistory.trend[0].excludedFromLearning)
      tryVerify(function() { return !activityGrid.cells.some(function(cell) { return cell.durationMs > 0 }) })
      sessionToggle = findVisual(sessionHistory, "plancks_sessionToggle_0")
      verify(!sessionToggle.checked)
      sessionToggle.forceActiveFocus(); keyClick(Qt.Key_Space)
      tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.rows[0].excludedFromStatistics === false })
      var detailButton = findVisual(sessionHistory, "plancks_sessionDetail_0")
      verify(detailButton.tooltipText.indexOf("View session totals") === 0)
      var sessionTimeHelp = findVisual(sessionHistory, "plancks_sessionTimeHelp_0")
      verify(sessionTimeHelp.helpText.indexOf(sessionHistory.fullStamp(Plancks.EpochController.sessionHistory.rows[0].start.utcMs)) === 0)
      panel.revealButton(sessionTimeHelp)
      wait(100)
      mouseMove(sessionTimeHelp, sessionTimeHelp.width / 2, sessionTimeHelp.height / 2)
      var sessionTimeTip = findChild(sessionTimeHelp, "plancks_sessionTimeHelp_0Tip")
      tryVerify(function() { return sessionTimeTip.visible })
      widget.setTooltipsEnabled(false)
      tryVerify(function() { return !sessionTimeTip.visible })
      compare(detailButton.tooltipText, "")
      widget.setTooltipsEnabled(true)
      detailButton.forceActiveFocus(); keyClick(Qt.Key_Return)
      verify(sessionHistory.detail !== null, "Session detail opens")
      wait(200)
      var closingDetail = sessionHistory.detail
      widget.close()
      verify(panel.showingHistory && sessionHistory.detail === closingDetail,
             "Closing preserves the current detail view during fade-out")
      tryVerify(function() { return !findChild(panel, "plancks_popup").visible })
      verify(!panel.showingHistory, "Navigation resets only after the panel is hidden")
      widget.open()
      verify(!panel.showingHistory && !panel.showingSettings, "Reopening begins at the main view")
      panel.openHistory()
      panel.sessionHistoryMode = true
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading })
      sessionHistory.detail = closingDetail
      var initialToggle = findVisual(sessionHistory, "plancks_sessionDetailToggle")
      var initialTrack = Array.from(initialToggle.children).find(function(item) {
        return item.width === initialToggle.trackWidth && item.height === initialToggle.trackHeight
      })
      var initialKnob = Array.from(initialTrack.children).find(function(item) {
        return item.width === initialToggle.knobSize && item.height === initialToggle.knobSize
      })
      compare(initialKnob.x, initialToggle.trackWidth - initialToggle.knobSize - initialToggle.knobInset,
              "Included state is positioned immediately when details open")
      var partialHelp = findVisual(sessionHistory, "plancks_sessionValueHelp_Partial activity")
      verify(partialHelp.helpText.indexOf("Time in stopped activity stages.") >= 0)
      verify(sessionsTab.selected, "Details remain within the Sessions tab")
      sessionsTab.forceActiveFocus()
      wait(150)
      compare(String(sessionsTab.color), String(Style.selectedFillFor(sessionsTab.foreground, sessionsTab.accent)), "Selected tab retains its fill with keyboard focus in details")
      verify(findChild(panel, "plancks_sessionDetailSummary").visible)
      compare(findChild(panel, "plancks_sessionDetailTotals").entries[1][0], "Partial activity")
      var totalsGrid = findChild(panel, "plancks_sessionDetailTotals")
      compare(totalsGrid.columns, 2, "Session totals pair records at normal width")
      totalsGrid.width = Style.space(280)
      tryCompare(totalsGrid, "columns", 1)
      totalsGrid.width = Qt.binding(function() { return totalsGrid.parent.width })
      tryCompare(totalsGrid, "columns", 2)
      var savedDetail = sessionHistory.detail
      var pagedDetail = JSON.parse(JSON.stringify(savedDetail))
      pagedDetail.stages = []
      for (var stageIndex = 0; stageIndex < 9; stageIndex++)
        pagedDetail.stages.push(Object.assign({}, savedDetail.stages[0], {round: stageIndex + 1}))
      sessionHistory.detail = pagedDetail
      var stageRows = findChild(sessionHistory, "plancks_stageRows")
      var stagesNext = findVisual(sessionHistory, "plancks_stagesNext")
      var stagesPrevious = findVisual(sessionHistory, "plancks_stagesPrevious")
      var stagesLabel = findVisual(sessionHistory, "plancks_stagesPageLabel")
      tryCompare(stageRows, "count", 4)
      compare(stagesLabel.text, "Page 1 of 3")
      verify(!stagesPrevious.enabled && stagesNext.enabled)
      stagesNext.forceActiveFocus(); keyClick(Qt.Key_Return)
      tryCompare(stagesLabel, "text", "Page 2 of 3")
      compare(stageRows.itemAt(0).modelData.round, 5, "Stages retain chronological order across pages")
      tryVerify(function() { return findVisual(sessionHistory, "plancks_stageHeading").activeFocus })
      stagesNext.forceActiveFocus(); keyClick(Qt.Key_Return)
      tryCompare(stageRows, "count", 1)
      compare(stagesLabel.text, "Page 3 of 3")
      compare(stageRows.itemAt(0).modelData.round, 9)
      verify(!stagesNext.enabled && stagesPrevious.enabled)
      stagesPrevious.forceActiveFocus(); keyClick(Qt.Key_Return)
      tryCompare(stagesLabel, "text", "Page 2 of 3")
      sessionHistory.detail = savedDetail
      tryCompare(stageRows, "count", savedDetail.stages.length)
      verify(!stagesNext.visible, "Single-page stage lists hide pagination")
      var detailToggle = findVisual(sessionHistory, "plancks_sessionDetailToggle")
      verify(detailToggle.checked)
      Plancks.EpochController.requestSessionHistory(0, "included", sessionHistory.detail.sessionId)
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading })
      detailToggle.forceActiveFocus(); keyClick(Qt.Key_Space)
      tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.sessionHistoryLoading && sessionHistory.detail.excludedFromStatistics === true })
      compare(Plancks.EpochController.sessionHistory.total, 0, "Detail stays available after filtering out its row")
      verify(!detailToggle.checked)
      detailToggle.forceActiveFocus(); keyClick(Qt.Key_Space)
      tryVerify(function() { return !Plancks.EpochController.busy && !Plancks.EpochController.sessionHistoryLoading && sessionHistory.detail.excludedFromStatistics === false })
      Plancks.EpochController.requestSessionHistory(0, "", sessionHistory.detail.sessionId)
      tryVerify(function() { return !Plancks.EpochController.sessionHistoryLoading })
      detailButton = findVisual(sessionHistory, "plancks_sessionDetail_0")

      wait(300)
      scroll.contentY = 0
      wait(100)
      mouseClick(back, back.width / 2, back.height / 2)
      wait(300)
      verify(sessionHistory.detail === null && panel.showingHistory && panel.sessionHistoryMode, "Mouse header Back returns to parent session list")
      detailButton.forceActiveFocus(); keyClick(Qt.Key_Return)
      verify(sessionHistory.detail !== null)
      scroll.contentY = 0
      wait(100)
      mouseClick(sessionsTab, sessionsTab.width / 2, sessionsTab.height / 2)
      verify(sessionHistory.detail === null && panel.showingHistory && panel.sessionHistoryMode, "Reclicking Sessions returns to the parent list")
      mouseClick(sessionsTab, sessionsTab.width / 2, sessionsTab.height / 2)
      verify(panel.showingHistory && panel.sessionHistoryMode, "Reclicking Sessions on the list stays on the list")
      wait(100)
      detailButton.forceActiveFocus(); keyClick(Qt.Key_Return)
      verify(sessionHistory.detail !== null)
      keys.forceActiveFocus(); keyClick(Qt.Key_Escape)
      verify(sessionHistory.detail === null && panel.showingHistory, "Detail Escape returns to session list")
      back.forceActiveFocus(); keyClick(Qt.Key_Return)
      verify(!panel.showingHistory, "Header Back from session list returns to epoch")
      panel.closeHistory()
      Plancks.EpochController.transition()
      tryVerify(function() { return widget.epoch.phase === "active" && !Plancks.EpochController.busy })
      console.log("SESSION_UI_HISTORY_OK")
      seedSession.withRest = true
      seedSession.running = true
      tryVerify(function() { return !seedSession.running && !!widget.epoch.session && widget.epoch.session.canAdvance }, 5000)
      compare(Plancks.EpochController.primaryActionLabel, "Start rest")
      compare(Plancks.EpochController.ipc.primaryAction(), "submitted")
      compare(Plancks.EpochController.ipc.primaryAction(), "repeat-ignored")
      tryVerify(function() { return !Plancks.EpochController.busy && widget.epoch.session.kind === "short_break" })
      compare(widget.epoch.phase, "active")
      Plancks.EpochController.sessionAction("session_stopped")
      tryVerify(function() { return !Plancks.EpochController.busy && !widget.epoch.session })
      wait(650)
      seedSession.withRest = false
      seedSession.running = true
      tryVerify(function() { return !seedSession.running && !!widget.epoch.session && widget.epoch.session.canAdvance }, 5000)
      tryVerify(function() { return Plancks.EpochController.notificationMessage.indexOf("time reached") >= 0 }, 5000)
      verify(widget.epoch.session.timer.indexOf("+") === 0, "Recovered target counts overrun")
      var finish = findChild(panel, "plancks_advanceSession")
      compare(finish.Accessible.name, "Finish session")
      compare(finish.text, "Finish")
      verify(finish.visible && finish.enabled, "Advance action appears at target")
      compare(finish.parent.parent, pause.parent, "Advance slot shares the session controls column")
      compare(finish.x, pause.x, "Session controls align")
      tryVerify(function() { return finish.parent.y + finish.y < pause.y }, 1000, "Advance appears above pause after layout")
      verify(!finish.selected && finish.bordered, "Advance uses the epoch button border without selected fill")
      compare(pause.y, pauseSlotY, "Pause stays fixed when advance appears")
      compare(findChild(panel, "plancks_stopSession").y, stopSlotY, "Stop stays fixed when advance appears")
      finish.forceActiveFocus(); keyClick(Qt.Key_Tab)
      verify(pause.activeFocus, "Tab follows visual order from advance to pause")
      keyClick(Qt.Key_Backtab)
      verify(finish.activeFocus, "Backtab returns to advance")
      compare(Plancks.EpochController.primaryActionLabel, "Finish session")
      Plancks.EpochController.sessionAction("session_paused")
      tryVerify(function() { return !Plancks.EpochController.busy && widget.epoch.session.status === "paused" })
      compare(Plancks.EpochController.ipc.primaryAction(), "controls-opened", "Paused overrun opens controls instead of finishing")
      verify(!!widget.epoch.session)
      Plancks.EpochController.sessionAction("session_resumed")
      tryVerify(function() { return !Plancks.EpochController.busy && widget.epoch.session.status === "running" })
      wait(650)
      compare(Plancks.EpochController.ipc.primaryAction(), "submitted")
      tryVerify(function() { return !widget.epoch.session && !Plancks.EpochController.busy })
      compare(widget.epoch.phase, "active", "Finishing session leaves epoch active")
      compare(Plancks.EpochController.ipc.primaryAction(), "repeat-ignored", "Repeat after session finish cannot end epoch")
      compare(widget.epoch.phase, "active")
      wait(650)
      compare(Plancks.EpochController.ipc.primaryAction(), "submitted")
      tryVerify(function() { return !Plancks.EpochController.busy && widget.epoch.phase === "off" })
      wait(650)
      compare(Plancks.EpochController.ipc.primaryAction(), "submitted")
      tryVerify(function() { return !Plancks.EpochController.busy && widget.epoch.phase === "active" })
      Plancks.EpochController.reset()
      tryVerify(function() { return widget.epoch.sequence === 0 && !Plancks.EpochController.busy })
      console.log("PLANCKS_SESSION_UI_PASS")
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
    # Exercise the paste helper without touching the desktop clipboard.
    reader_dir = root / 'bin'
    reader_dir.mkdir()
    reader = reader_dir / 'wl-paste'
    reader.write_text('#!/bin/sh\nprintf "20, 1"\n')
    reader.chmod(0o755)
    env = dict(os.environ, XDG_STATE_HOME=str(root / 'state'), PLANCKS_DISABLE_NOTIFICATIONS='1',
               PATH=str(reader_dir) + os.pathsep + os.environ.get('PATH', ''))
    try:
        result = subprocess.run(['quickshell', '-p', str(root), '--no-color'],
                                env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=90)
    except subprocess.TimeoutExpired as exc:
        print((exc.stdout or b'').decode(errors='replace'))
        raise
    print(result.stdout)
    if result.returncode or 'PLANCKS_SMOKE_PASS' not in result.stdout or 'SMOKE_FAIL' in result.stdout or ' ERROR' in result.stdout or 'WARN scene:' in result.stdout or 'FAIL!' in result.stdout or (args.preview and ('PLANCKS_RESET_UI_PASS' not in result.stdout or 'PLANCKS_SESSION_UI_PASS' not in result.stdout)):
        raise SystemExit(1)
