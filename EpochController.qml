pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "Graphics.js" as Graphics

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
    property var session: null
    property string epochId: ""
  }
  property var history: ({rows: [], page: 0, pages: 1, total: 0})
  property bool historyLoading: false
  property string historyError: ""
  property string historyRequestId: ""
  property int historyPage: 0
  property string historyQuery: ""

  function requestHistory(page, query) {
    if (query !== undefined) historyQuery = query
    historyPage = Math.max(0, page)
    historyError = ""
    historyLoading = true
    historyRequestId = "history-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2)
    if (helper.running) {
      helper.write(JSON.stringify({action: "history", page: historyPage, query: historyQuery, requestId: historyRequestId}) + "\n")
      historyWatchdog.restart()
    } else helper.running = true
  }

  function setSessionInclusion(sessionId, excluded) {
    if (!ready || busy || sessionHistoryLoading) return
    sendAction("session_inclusion_changed", sessionHistory.generation, sessionHistory.sequence, false,
      {sessionId: sessionId, excludedFromStatistics: excluded})
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
  property string insightsError: ""
  property string notificationMessage: ""
  property string notificationImage: ""
  property var noticeQueue: []
  function deliverNotice(message) {
    noticeQueue = noticeQueue.concat([{message: message, image: decodeURIComponent(Qt.resolvedUrl(Graphics.notificationImage(settings.animatedGraphic, state)).toString().replace(/^file:\/\//, ""))}])
    if (!notification.running) nextNotice()
  }
  function nextNotice() {
    if (!noticeQueue.length) return
    notificationMessage = noticeQueue[0].message
    notificationImage = noticeQueue[0].image
    noticeQueue = noticeQueue.slice(1)
    insightDelivered(notificationMessage)
    if (Quickshell.env("PLANCKS_DISABLE_NOTIFICATIONS") !== "1") notification.running = true
    else if (noticeQueue.length) Qt.callLater(nextNotice)
  }
  signal insightDelivered(string message)
  function requestInsightPreview() {
    if (helper.running) helper.write(JSON.stringify({action: "preview_insight"}) + "\n")
  }
  property Process notification: Process {
    command: ["python3", decodeURIComponent(Qt.resolvedUrl("notification_send.py").toString().replace(/^file:\/\//, ""))]
    stdinEnabled: true
    onStarted: write(JSON.stringify({message: root.notificationMessage, image: root.notificationImage}) + "\n")
    onExited: function(code, status) {
      if (code !== 0) root.insightsError = "Could not deliver the notification. Check that desktop notifications and Python GObject are available."
      Qt.callLater(root.nextNotice)
    }
  }


  function configure(values) {
    settings = values || {}
    if (helper.running)
      helper.write(JSON.stringify({action: "configure", initialSeconds: Number(settings.initialSeconds || 0),
        insightsEnabled: settings.insightsEnabled === true,
        finishNotificationsEnabled: settings.finishNotificationsEnabled === true,
        insightFrequency: settings.insightFrequency || "standard",
        finishWarningSeconds: settings.finishWarningSeconds || [1800, 60]}) + "\n")
  }

  property var panels: []
  property var lastPanel: null
  property var endIntent: null
  signal sessionStarted(var config)
  property var sessionHistory: ({rows: [], page: 0, pages: 1, total: 0})
  property bool sessionHistoryLoading: false
  property string sessionHistoryError: ""
  property string sessionHistoryId: ""
  property string sessionQuery: ""
  function registerPanel(panel) { panels = panels.concat([panel]) }
  function unregisterPanel(panel) { if (lastPanel === panel) lastPanel = null; panels = panels.filter(function(p) { return p !== panel }); if (endIntent && endIntent.panel === panel) endIntent = null }
  function requestSessionHistory(page, query, detailId) {
    if (query !== undefined) sessionQuery = query
    sessionHistoryLoading = true
    sessionHistoryError = ""
    sessionHistoryId = "sessions-" + Date.now() + "-" + Math.random()
    if (helper.running) helper.write(JSON.stringify({action: "session_history", page: page || 0, query: sessionQuery, detailId: detailId || null, requestId: sessionHistoryId}) + "\n")
    sessionHistoryWatchdog.restart()
  }
  property Timer sessionHistoryWatchdog: Timer {
    interval: 10000
    onTriggered: { root.sessionHistoryLoading = false; root.sessionHistoryError = "No response. Retry session history." }
  }
  function sessionAction(action, config) {
    if (!ready || busy || (!config && !state.session)) return
    var extra = config ? {config: config} : {sessionId: state.session.sessionId, stageId: state.session.stageId}
    sendAction(action, undefined, undefined, false, extra)
  }
  readonly property string primaryActionLabel: endIntent ? "Review epoch confirmation" : !state.session
    ? (state.phase === "active" ? "End epoch" : "Start epoch")
    : state.session.status === "paused" || !state.session.canAdvance
      ? "Open session controls" : state.session.nextLabel
  // Require a quiet interval between shortcut invocations. Repeated IPC calls
  // cannot finish a session and then immediately end its parent epoch.
  property Timer primaryRepeatGuard: Timer { interval: 600 }
  function primaryAction() {
    if (primaryRepeatGuard.running) { primaryRepeatGuard.restart(); return "repeat-ignored" }
    if (busy) return "busy"
    if (!ready) return "not-ready"
    if (endIntent) return "confirmation-pending"
    primaryRepeatGuard.restart()
    if (!state.session) return transition()
    if (state.session.status === "paused" || !state.session.canAdvance) {
      var panel = panels.filter(function(p) { return p.opened })[0] || lastPanel || panels[0]
      if (!panel) return "not-ready"
      panel.showSessionControls()
      return "controls-opened"
    }
    sessionAction(state.session.final ? "session_completed" : "session_advanced")
    return "submitted"
  }
  function transition(skipLearning, sourcePanel) {
    if (!ready || busy) return "not-ready"
    if (state.phase === "active" && state.session) {
      if (!endIntent) {
        var panel = sourcePanel || panels.filter(function(p) { return p.opened })[0] || lastPanel || panels[0]
        if (!panel) return "not-ready"
        endIntent = {panel: panel, sessionId: state.session.sessionId, epochId: state.epochId,
                     generation: state.generation, skip: skipLearning === true}
        panel.showEpochEndConfirmation()
      }
      return "confirmation-pending"
    }
    sendAction(state.phase === "active" ? "end" : "start", undefined, undefined, skipLearning === true)
    return "submitted"
  }
  function cancelEpochEnd() { endIntent = null }
  function confirmEpochEnd() {
    if (!endIntent || busy || !ready) return
    var intent = endIntent
    if (intent.generation !== state.generation || intent.epochId !== state.epochId || !state.session || intent.sessionId !== state.session.sessionId) {
      intent.panel.cancelEpochEndConfirmation()
      error = "Session changed. Review the current epoch."
      return
    }
    sendAction("end", intent.generation, state.sequence, intent.skip, {cascadeSessionId: intent.sessionId})
  }

  property IpcHandler ipc: IpcHandler {
    target: "gregl83.plancks"

    function primaryAction(): string { return root.primaryAction() }

    function toggleEpoch(): string {
      if (root.busy) return "busy"
      if (!root.ready) return "not-ready"
      return root.transition()
    }

    function toggleEpochSkip(): string {
      if (root.busy) return "busy"
      if (!root.ready) return "not-ready"
      return root.transition(true)
    }
  }

  function reset(generation, sequence) {
    if (busy) return
    noticeQueue = []
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
          if (result.insightsError !== undefined) {
            root.insightsError = result.insightsError
            return
          }
          if (result.sessionNotice) {
            if (root.pendingCommand && root.pendingCommand.action === "reset") return
            if (root.ready && result.sessionNotice.generation !== root.state.generation) return
            result.insight = result.sessionNotice
          }
          if (result.insight) {
            if (result.view) root.applyView(result.view)
            root.deliverNotice(result.insight.message)
            return
          }
          if (result.requestId && result.requestId.indexOf("sessions-") === 0) {
            if (result.requestId !== root.sessionHistoryId) return
            root.sessionHistoryWatchdog.stop()
            root.sessionHistoryLoading = false
            if (result.ok) root.sessionHistory = result.sessionHistory
            else root.sessionHistoryError = result.error || "Unable to load sessions"
            return
          }
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
              if (root.pendingCommand && root.pendingCommand.action === "session_started") root.sessionStarted(root.pendingCommand.config)
              if (root.endIntent && root.pendingCommand && root.pendingCommand.action === "end") root.endIntent.panel.cancelEpochEndConfirmation()
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
      root.sessionHistoryWatchdog.stop()
      root.sessionHistoryLoading = false
      root.sessionHistoryError = "Plancks storage stopped. Retry session history after reconnecting."
      root.historyLoading = false
      root.historyError = "Plancks storage stopped. Select Retry to reconnect."
      root.ready = false
      root.busy = false
      root.error = "Plancks storage stopped. Select Retry to reconnect."
    }
  }
}
