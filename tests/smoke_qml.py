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
      if (!test.check(test.attempts < 40, "helper timeout at step " + test.step + ": " + Plancks.EpochController.error)) return
      if (!test.ipcDone || !Plancks.EpochController.ready || Plancks.EpochController.busy) return
      if (test.step === 0) {
        if (!test.check(widget.epoch.phase === "off", "initial phase")) return
        Plancks.EpochController.busy = true
        if (!test.check(Plancks.EpochController.ipc.toggleEpoch() === "busy", "IPC busy guard")) return
        if (!test.check(Plancks.EpochController.ipc.toggleEpochSkip() === "busy", "skip IPC busy guard")) return
        Plancks.EpochController.busy = false
        Plancks.EpochController.ready = false
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
      compare(Plancks.EpochController.state.sequence, tooltipSequence, "Preview does not change epoch history")
      keyClick(Qt.Key_Tab)
      verify(finishToggle.activeFocus && !finishToggle.checked, "Finish notifications are independent")
      keyClick(Qt.Key_Space)
      verify(widget.finishNotificationsEnabled, "Finish notifications can be enabled")
      keyClick(Qt.Key_Tab)
      verify(warningMinutes.activeFocus, "Warning minutes are editable")
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
      verify(historyView.visible)
      var back = findChild(panel, "plancks_historyBackButton")
      tryVerify(function() { return !Plancks.EpochController.historyLoading })
      compare(Plancks.EpochController.history.total, 3, "Three completed intervals before paging")
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
    env = dict(os.environ, XDG_STATE_HOME=str(root / 'state'), PLANCKS_DISABLE_NOTIFICATIONS='1')
    try:
        result = subprocess.run(['quickshell', '-p', str(root), '--no-color'],
                                env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=35)
    except subprocess.TimeoutExpired as exc:
        print((exc.stdout or b'').decode(errors='replace'))
        raise
    print(result.stdout)
    if result.returncode or 'PLANCKS_SMOKE_PASS' not in result.stdout or 'SMOKE_FAIL' in result.stdout or ' ERROR' in result.stdout or 'WARN scene:' in result.stdout or 'FAIL!' in result.stdout or (args.preview and 'PLANCKS_RESET_UI_PASS' not in result.stdout):
        raise SystemExit(1)
