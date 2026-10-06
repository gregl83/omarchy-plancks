pragma Singleton
import QtQuick
import Quickshell.Io

QtObject {
  id: root
  // Keep this object stable. Updating one property must not invalidate every
  // label, forecast, and panel row on every second tick.
  readonly property QtObject state: QtObject {
    property string phase: "off"
    property int sequence: 0
    property string generation: ""
    property string indicator: "○"
    property string timer: "--:--:--"
    property string status: "Loading Plancks…"
    property string elapsed: "00:00:00"
    property var timeBasis: null
    property var lastStartUtcMs: null
    property var lastEndUtcMs: null
    property var predictedEndUtcMs: null
    property var predictedStartUtcMs: null
    property var workPredictionMs: null
    property var gapPredictionMs: null
    property int workSampleCount: 0
    property int gapSampleCount: 0
    property var warnings: []
  }
  property var history: ({rows: [], page: 0, pages: 1, total: 0})
  property bool historyLoading: false
  property string historyError: ""
  property string historyRequestId: ""
  property int historyPage: 0

  function requestHistory(page) {
    historyPage = Math.max(0, page)
    historyError = ""
    historyLoading = true
    historyRequestId = "history-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2)
    if (helper.running) {
      helper.write(JSON.stringify({action: "history", page: historyPage, requestId: historyRequestId}) + "\n")
      historyWatchdog.restart()
    } else helper.running = true
  }

  function setHistoryInclusion(sampleId, excluded) {
    if (!ready || busy || historyLoading) return
    sendAction("set_inclusion", history.generation, history.sequence, false,
      {sampleId: sampleId, excludedFromLearning: excluded})
  }

  property Timer historyWatchdog: Timer {
    interval: 10000
    onTriggered: {
      root.historyLoading = false
      root.historyError = "No response from Plancks storage. Select Retry to load history."
    }
  }

  property int openPanels: 0

  function setPanelOpen(opened) {
    var wasOpen = openPanels > 0
    openPanels = Math.max(0, openPanels + (opened ? 1 : -1))
    if (helper.running && wasOpen !== (openPanels > 0))
      helper.write(JSON.stringify({action: "panel", open: openPanels > 0}) + "\n")
  }

  function applyView(values) {
    for (var key in values) {
      if (!(key in state)) continue
      if (key === "warnings") {
        if (JSON.stringify(state.warnings) !== JSON.stringify(values.warnings)) state.warnings = values.warnings
      } else if (state[key] !== values[key]) state[key] = values[key]
    }
  }
  property bool ready: false
  property bool busy: false
  property string error: ""
  property string pendingId: ""
  property var settings: ({})
  property var pendingCommand: null

  function configure(values) {
    settings = values || {}
    if (helper.running)
      helper.write(JSON.stringify({action: "configure", initialSeconds: Number(settings.initialSeconds || 0)}) + "\n")
  }

  function transition(skipLearning) {
    if (!ready || busy) return
    sendAction(state.phase === "active" ? "end" : "start", undefined, undefined, skipLearning === true)
  }

  property IpcHandler ipc: IpcHandler {
    target: "gregl83.plancks"

    function toggleEpoch(): string {
      if (root.busy) return "busy"
      if (!root.ready) return "not-ready"
      root.transition()
      return "submitted"
    }

    function toggleEpochSkip(): string {
      if (root.busy) return "busy"
      if (!root.ready) return "not-ready"
      root.transition(true)
      return "submitted"
    }
  }

  function reset(generation, sequence) {
    if (busy) return
    sendAction("reset", generation, sequence)
  }

  function sendAction(action, generation, sequence, skipLearning, extra) {
    busy = true
    error = ""
    pendingId = Date.now().toString(36) + "-" + Math.random().toString(36).slice(2)
    pendingCommand = {action: action, skipLearning: skipLearning === true, generation: generation === undefined ? state.generation : generation,
      requestId: pendingId, sequence: sequence === undefined ? state.sequence : sequence,
      rotateBytes: Number(settings.rotateBytes || 5242880)}
    if (extra) for (var key in extra) pendingCommand[key] = extra[key]
    if (!helper.running) helper.running = true
    else helper.write(JSON.stringify(pendingCommand) + "\n")
    watchdog.restart()
  }

  function retry() {
    error = ""
    if (!helper.running) helper.running = true
    else if (pendingCommand) {
      busy = true
      helper.write(JSON.stringify(pendingCommand) + "\n")
      watchdog.restart()
    } else configure(settings)
  }

  property Timer watchdog: Timer {
    interval: 10000
    onTriggered: {
      root.busy = false
      root.ready = false
      root.error = "No response from Plancks storage. Select Retry to check whether the action was saved."
    }
  }

  property Process helper: Process {
    command: ["python3", "-u", decodeURIComponent(Qt.resolvedUrl("plancks.py").toString().replace(/^file:\/\//, "")), "serve"]
    stdinEnabled: true
    running: true
    onStarted: {
      root.configure(root.settings)
      if (root.historyLoading) root.requestHistory(root.historyPage)
      if (root.openPanels > 0) write(JSON.stringify({action: "panel", open: true}) + "\n")
      if (root.pendingCommand) {
        root.busy = true
        write(JSON.stringify(root.pendingCommand) + "\n")
        root.watchdog.restart()
      }
    }
    stdout: SplitParser {
      onRead: function(line) {
        try {
          var result = JSON.parse(line)
          if (result.requestId && result.requestId.indexOf("history-") === 0) {
            if (result.requestId !== root.historyRequestId) return
            root.historyWatchdog.stop()
            root.historyLoading = false
            if (result.ok && result.history) {
              root.history = result.history
              root.historyPage = result.history.page
            } else root.historyError = result.error || "Unable to load history"
            return
          }
          if (result.ok) {
            root.applyView(result.view || result.patch || {})
            root.ready = !root.pendingCommand
          } else {
            if (result.generation !== undefined) root.state.generation = result.generation
            root.error = result.error || "Unable to read Plancks state"
            root.ready = false
          }
          if (result.requestId && result.requestId === root.pendingId) {
            root.watchdog.stop()
            root.busy = false
            if (result.ok) {
              root.pendingCommand = null
              root.pendingId = ""
              root.error = ""
              root.ready = true
            } else {
              // Retry uncertain I/O outcomes with the same ID. A rejected stale
              // command is definitive; the next status will enable a fresh action.
              if (!result.retryable) {
                root.pendingCommand = null
                root.pendingId = ""
              }
              root.ready = false
            }
          }
        } catch (e) {
          root.error = "Invalid response from Plancks storage: " + e
          root.ready = false
        }
      }
    }
    stderr: SplitParser {
      onRead: function(line) { if (line.trim()) root.error = line.trim() }
    }
    onExited: function(code, status) {
      root.watchdog.stop()
      root.historyWatchdog.stop()
      root.historyLoading = false
      root.historyError = "Plancks storage stopped. Select Retry to reconnect."
      root.ready = false
      root.busy = false
      root.error = "Plancks storage stopped. Select Retry to reconnect."
    }
  }
}
