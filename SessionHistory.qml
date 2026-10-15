import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "."

Column {
  id: root
  property var backControl: null
  property bool tooltipsEnabled: true
  property string fontFamily: Style.font.family
  signal pageChanged()
  signal stagePageChanged(var heading)
  function changePage(page) {
    focusSessionId = ""
    EpochController.requestSessionHistory(page)
    pageChanged()
  }
  property color foreground: Color.foreground
  property var detail: null
  property string focusSessionId: ""
  onHistoryChanged: {
    if (!visible) return
    if (detail) {
      var updated = history.detail && history.detail.sessionId === detail.sessionId ? history.detail
        : history.rows.find(function(row) { return row.sessionId === root.detail.sessionId })
      if (updated) detail = updated
    }
    if (focusSessionId) Qt.callLater(function() {
      for (var i = 0; i < sessionRows.count; i++) {
        var row = sessionRows.itemAt(i)
        if (row && row.modelData.sessionId === root.focusSessionId) { row.focusInclusion(); break }
      }
    })
  }
  readonly property var history: EpochController.sessionHistory
  signal backRequested()
  signal revealRequested(var item)
  spacing: Style.space(12)
  function length(ms) { var s = Math.max(0, Math.floor(ms / 1000)); return Math.floor(s / 3600).toString().padStart(2, "0") + ":" + Math.floor(s / 60 % 60).toString().padStart(2, "0") + ":" + (s % 60).toString().padStart(2, "0") }
  function compactLength(ms) {
    var minutes = Math.floor(Math.abs(ms) / 60000)
    return minutes === 0 ? (ms === 0 ? "0m" : "<1m")
      : minutes >= 60 ? Math.floor(minutes / 60) + "h" + (minutes % 60 ? " " + minutes % 60 + "m" : "") : minutes + "m"
  }
  function durationRecord(label, ms) { return [label, compactLength(ms), length(ms)] }
  function sessionTitle(config) { return config.name ? config.name : config.preset === "pomodoro" ? "Pomodoro" : "Custom" }
  function stamp(ms) { return Qt.formatDateTime(new Date(ms), "ddd, MMM d yyyy HH:mm") }
  function fullStamp(ms) { return Qt.formatDateTime(new Date(ms), "ddd, MMM d, yyyy · HH:mm:ss") }
  function timeRange(session) { return session ? fullStamp(session.start.utcMs) + " → " + fullStamp(session.end.utcMs) : "" }
  function valueHelp(entry) {
    var explanations = {"Completed rounds": "Activity rounds completed manually.",
      "Completed activity": "Time in completed activity stages.", "Partial activity": "Time in stopped activity stages.",
      "Rest": "Rest duration.", "Paused": "Paused time; excluded from stage duration.",
      "Planned": "Configured stage duration.", "Actual": "Elapsed stage time, excluding pauses.",
      "Difference": "Actual minus planned duration.", "Overrun": "Time beyond the stage target, excluding pauses.",
      "Activity": "Configured duration of each activity stage.", "Long rest": "Long-rest duration and cadence.",
      "Final rest": "Whether a rest follows the final activity round.", "Parent epoch": "Epoch containing this session."}
    var explanation = entry[3] || explanations[entry[0]]
    return entry[0] + ": " + (entry[2] || entry[1]) + (explanation ? "\n" + explanation : "")
  }
  component HoverHelp: MouseArea {
    id: helpHover
    property string helpText: ""
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.NoButton
    PanelToolTip {
      objectName: helpHover.objectName + "Tip"
      visible: root.tooltipsEnabled && helpHover.containsMouse
      text: helpHover.helpText
      fontFamily: root.fontFamily
    }
  }
  function searchHistory() {
    delay.stop()
    focusSessionId = ""
    EpochController.requestSessionHistory(0, search.text)
  }
  function clearHistorySearch() {
    search.text = ""
    searchHistory()
    search.forceActiveFocus()
  }
  onVisibleChanged: {
    if (!visible) { detail = null; focusSessionId = ""; delay.stop() }
    else if (search.text !== EpochController.sessionQuery) searchHistory()
    else EpochController.requestSessionHistory(0)
  }
  onDetailChanged: if (detail) delay.stop()

  Keys.onEscapePressed: backRequested()
  Connections {
    target: EpochController.state
    function onSequenceChanged() { if (root.visible) EpochController.requestSessionHistory(root.history.page, undefined, root.detail ? root.detail.sessionId : null) }
    function onGenerationChanged() { root.detail = null; if (root.visible) EpochController.requestSessionHistory(0) }
  }
  Column {
    width: parent.width
    visible: !root.detail
    spacing: Style.space(8)
    Row {
      width: parent.width
      spacing: Style.space(20)
      HistoryTrend {
        id: focusTrend
        objectName: "plancks_sessionFocusTrend"
        width: (parent.width - parent.spacing) / 2
        title: "Activity time"
        sessionTrend: true
        plotHeight: activityGrid.gridHeight
        points: root.history.trend || []
        foreground: root.foreground
        fontFamily: root.fontFamily
        tooltipsEnabled: root.tooltipsEnabled
      }
      SessionActivity {
        id: activityGrid
        objectName: "plancks_sessionActivity"
        width: (parent.width - parent.spacing) / 2
        visible: focusTrend.visible
        activity: root.history.activity || ({})
        foreground: root.foreground
        fontFamily: root.fontFamily
        tooltipsEnabled: root.tooltipsEnabled
      }
    }
    Text {
      width: parent.width
      visible: focusTrend.points.length > 0 && !!root.history.query
      text: "Activity charts · unaffected by search"
      color: root.foreground
      opacity: 0.6
      font.family: root.fontFamily
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
    }
    Text { width: parent.width; visible: !root.detail; text: "Epoch totals · " + (root.history.completedRounds || 0) + " rounds · " + root.length(root.history.completedFocusMs || 0) + " activity"
      color: root.foreground; opacity: 0.6; font.pixelSize: Style.font.caption; font.family: root.fontFamily; wrapMode: Text.WordWrap }
    PanelSeparator { foreground: root.foreground }
  }
  Row {
    width: parent.width
    visible: !root.detail
    spacing: Style.space(8)
    BoundedTextField {
      id: search
      objectName: "plancks_sessionSearch"
      width: parent.width - (clearSearch.visible ? clearSearch.width + parent.spacing : 0)
      placeholderText: "Search dates, times, durations…"
      Component.onCompleted: text = EpochController.sessionQuery
      foreground: root.foreground
      maximumLength: 256
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
      Accessible.name: "Search sessions"
      Accessible.description: "Search names, presets, dates, times, durations, and status."
      onTextChanged: if (root.visible && text !== EpochController.sessionQuery) delay.restart()
      onAccepted: root.searchHistory()
      Keys.onEscapePressed: { if (text.length) root.clearHistorySearch(); else root.backRequested() }
      onActiveFocusChanged: if (activeFocus) root.revealRequested(search)
    }
    Button {
      id: clearSearch
      objectName: "plancks_sessionsClearSearch"
      anchors.verticalCenter: search.verticalCenter
      visible: search.text.length > 0
      text: "Clear"
      foreground: root.foreground
      fontFamily: root.fontFamily
      fontSize: Style.font.caption
      horizontalPadding: Style.space(4)
      focusable: true
      bordered: false
      onClicked: root.clearHistorySearch()
      Keys.onEscapePressed: root.backRequested()
    }
  }
  Timer { id: delay; interval: 250; onTriggered: root.searchHistory() }
  Text {
    objectName: "plancks_sessionsSearchCount"
    width: parent.width
    visible: !root.detail && !!root.history.query
    text: EpochController.sessionHistoryLoading ? "Searching…"
      : root.history.total + (root.history.total === 1 ? " matching session" : " matching sessions")
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
  Text {
    width: parent.width
    visible: !root.detail && root.history.total === 0 && EpochController.sessionHistoryError === "" && EpochController.error === ""
    text: EpochController.sessionHistoryLoading ? "Loading history…"
      : root.history.query ? "No matching sessions." : "No completed sessions yet."
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
  }
  Text {
    width: parent.width
    visible: !root.detail && text.length > 0
    text: EpochController.sessionHistoryError || EpochController.error
    color: root.foreground
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    wrapMode: Text.WordWrap
  }
  Button { visible: EpochController.sessionHistoryError.length > 0; text: "Retry"; foreground: root.foreground; focusable: true
    onClicked: EpochController.requestSessionHistory(root.history.page, search.text) }
  Column {
    width: parent.width; visible: !root.detail; spacing: Style.space(8)
    Repeater {
      id: sessionRows
      model: root.history.rows
      delegate: Column {
        id: sessionRow
        required property var modelData
        required property int index
        function focusInclusion() { inclusion.forceActiveFocus() }
        width: root.width; spacing: Style.space(6)
        PanelSeparator { visible: sessionRow.index > 0; foreground: root.foreground }
        Item {
          width: parent.width
          implicitHeight: Math.max(rowDetails.implicitHeight, viewControl.implicitHeight, inclusionControl.implicitHeight)
          height: implicitHeight
          Column {
            id: rowDetails
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(0, parent.width - viewControl.width - inclusionControl.width - Style.space(24))
            spacing: Style.spacing.labelGap
            Text {
              id: rowTitle
              width: parent.width
              text: root.sessionTitle(sessionRow.modelData.config) + " · "
                + Qt.formatDateTime(new Date(sessionRow.modelData.start.utcMs),
                  new Date(sessionRow.modelData.start.utcMs).getFullYear() === new Date().getFullYear()
                    ? "ddd, MMM d" : "MMM d, yyyy")
                + (sessionRow.modelData.status === "stopped" ? " · Stopped" : "")
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
              font.weight: Font.Medium
              wrapMode: Text.WordWrap
            }
            Text {
              id: rowTiming
              HoverHelp {
                objectName: "plancks_sessionTimeHelp_" + sessionRow.index
                helpText: root.timeRange(sessionRow.modelData)
              }
              width: parent.width
              readonly property bool sameDay: Qt.formatDateTime(new Date(sessionRow.modelData.start.utcMs), "yyyy-MM-dd")
                === Qt.formatDateTime(new Date(sessionRow.modelData.end.utcMs), "yyyy-MM-dd")
              text: Qt.formatDateTime(new Date(sessionRow.modelData.start.utcMs), sameDay ? "HH:mm" : "MMM d HH:mm") + " → "
                + Qt.formatDateTime(new Date(sessionRow.modelData.end.utcMs), sameDay ? "HH:mm" : "MMM d HH:mm")
                + " · " + sessionRow.modelData.completedRounds + "/" + sessionRow.modelData.config.rounds + " rounds"
              textFormat: Text.PlainText
              color: root.foreground
              opacity: 0.6
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
              wrapMode: Text.WordWrap
            }
          }
          Column {
            id: inclusionControl
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(inclusion.implicitWidth, inclusionLabel.implicitWidth)
            spacing: Style.space(2)
            ToggleSwitch {
              id: inclusion
              objectName: "plancks_sessionToggle_" + sessionRow.index
              anchors.horizontalCenter: parent.horizontalCenter
              trackHeight: Style.space(16)
              cursorPad: Style.space(4)
              checked: !sessionRow.modelData.invalid && !sessionRow.modelData.excludedFromStatistics
              enabled: EpochController.ready && !EpochController.busy && !EpochController.sessionHistoryLoading
                && !sessionRow.modelData.invalid
              foreground: root.foreground
              activeFocusOnTab: true
              hasCursor: activeFocus
              Accessible.role: Accessible.CheckBox
              Accessible.name: "Use session for statistics"
              Accessible.description: sessionRow.modelData.invalid ? "Excluded: clock changed" : checked ? "Included" : "Excluded"
              Accessible.checkable: true
              Accessible.checked: checked
              onActiveFocusChanged: if (activeFocus) root.revealRequested(sessionRow)
              Keys.onSpacePressed: if (enabled) toggled()
              Keys.onReturnPressed: if (enabled) toggled()
              Keys.onEnterPressed: if (enabled) toggled()
              onToggled: {
                if (!enabled) return
                forceActiveFocus()
                root.focusSessionId = sessionRow.modelData.sessionId
                EpochController.setSessionInclusion(sessionRow.modelData.sessionId, checked)
              }
              PanelToolTip {
                visible: root.tooltipsEnabled && inclusion.containsMouse
                text: "Use for statistics · " + (sessionRow.modelData.invalid ? "Excluded: clock changed" : inclusion.checked ? "Included" : "Excluded")
                fontFamily: root.fontFamily
              }
            }
            Text {
              id: inclusionLabel
              anchors.horizontalCenter: parent.horizontalCenter
              text: inclusion.checked ? "Included" : "Excluded"
              color: root.foreground
              opacity: inclusion.checked ? 0.75 : 0.55
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
          }
          Column {
            id: viewControl
            anchors.right: inclusionControl.left
            anchors.rightMargin: Style.space(12)
            y: inclusionControl.y + inclusion.y + inclusion.height / 2 - height / 2
            width: viewButton.implicitWidth
            spacing: Style.space(2)
            Button {
              id: viewButton
              objectName: "plancks_sessionDetail_" + sessionRow.index
              anchors.horizontalCenter: parent.horizontalCenter
              text: "View"
              foreground: Qt.darker(root.foreground, 1.4)
              fontFamily: root.fontFamily
              fontSize: Style.font.caption
              horizontalPadding: Style.space(8)
              verticalPadding: Style.space(2)
              focusable: true
              bordered: false
              Accessible.name: "View session: " + rowTitle.text
              Accessible.description: rowTiming.text + ", " + sessionRow.modelData.status
              tooltipText: root.tooltipsEnabled ? "View session totals, stages, and saved settings." : ""
              onClicked: { root.focusSessionId = ""; root.detail = sessionRow.modelData; root.revealRequested(root) }
              onActiveFocusChanged: if (activeFocus) root.revealRequested(sessionRow)
            }

          }
        }
      }
    }
    PanelSeparator { foreground: root.foreground }
    Item {
      id: pagination
      width: parent.width
      readonly property real navigationWidth: Math.max(previousButton.implicitWidth, nextButton.implicitWidth)
      implicitHeight: Math.max(previousButton.implicitHeight, nextButton.implicitHeight, pageLabel.implicitHeight)
      height: implicitHeight
      Button {
        id: previousButton
        width: pagination.navigationWidth
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        objectName: "plancks_sessionsPrevious"
        text: "Previous"
        foreground: root.foreground
        fontFamily: root.fontFamily
        fontSize: Style.font.bodySmall
        horizontalPadding: Style.space(8)
        bordered: enabled
        focusable: enabled
        opacity: enabled ? 1 : 0.35
        enabled: !EpochController.sessionHistoryLoading && root.history.page > 0
        onActiveFocusChanged: if (activeFocus) root.revealRequested(previousButton)
        onClicked: if (enabled) root.changePage(root.history.page - 1)
      }
      Text {
        id: pageLabel
        objectName: "plancks_sessionsPageLabel"
        width: Math.max(0, parent.width - pagination.navigationWidth * 2 - Style.space(16))
        anchors.centerIn: parent
        text: "Page " + (root.history.page + 1) + " of " + root.history.pages
        textFormat: Text.PlainText
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        color: root.foreground
        opacity: 0.6
        font.family: root.fontFamily
        font.pixelSize: Style.font.bodySmall
      }
      Button {
        id: nextButton
        width: pagination.navigationWidth
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        objectName: "plancks_sessionsNext"
        text: "Next"
        foreground: root.foreground
        fontFamily: root.fontFamily
        fontSize: Style.font.bodySmall
        horizontalPadding: Style.space(8)
        bordered: enabled
        focusable: enabled
        opacity: enabled ? 1 : 0.35
        enabled: !EpochController.sessionHistoryLoading && root.history.page + 1 < root.history.pages
        onActiveFocusChanged: if (activeFocus) root.revealRequested(nextButton)
        onClicked: if (enabled) root.changePage(root.history.page + 1)
        KeyNavigation.tab: root.backControl
      }
    }
  }
  component DetailValues: GridLayout {
    id: values
    property var entries: []
    property bool singleColumn: false
    columns: !singleColumn && width >= Style.space(320) ? 2 : 1
    columnSpacing: Style.space(20)
    rowSpacing: Style.spacing.labelGap
    Repeater {
      model: values.entries
      delegate: Item {
        required property var modelData
        Layout.fillWidth: true
        Layout.preferredWidth: (values.width - values.columnSpacing * (values.columns - 1)) / values.columns
        implicitHeight: Math.max(label.implicitHeight, value.implicitHeight)
        height: implicitHeight
        HoverHelp {
          objectName: "plancks_sessionValueHelp_" + modelData[0]
          helpText: root.valueHelp(modelData)
        }
        Text {
          id: label
          width: Math.max(0, parent.width - value.width - Style.space(8))
          text: modelData[0]
          textFormat: Text.PlainText
          color: root.foreground
          opacity: 0.6
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
        Text {
          id: value
          anchors.right: parent.right
          width: Math.min(implicitWidth, parent.width * 0.6)
          text: modelData[1]
          textFormat: Text.PlainText
          color: root.foreground
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          horizontalAlignment: Text.AlignRight
          wrapMode: Text.WordWrap
        }
      }
    }
  }
  Loader {
    width: parent.width
    active: !!root.detail
    visible: active
    // Initialize controls with the selected session's state, rather than
    // animating a persistent empty view from unchecked to included on entry.
    sourceComponent: Column {
    id: detailView
    objectName: "plancks_sessionDetailSummary"
    readonly property var session: root.detail
    property int stagePage: 0
    readonly property int stagePages: Math.max(1, Math.ceil((session ? session.stages.length : 0) / 4))
    onStagePagesChanged: stagePage = Math.min(stagePage, stagePages - 1)
    function changeStagePage(page) {
      stagePage = Math.max(0, Math.min(stagePages - 1, page))
      Qt.callLater(function() { stageHeading.forceActiveFocus(); root.stagePageChanged(stageHeading) })
    }
    width: parent.width
    visible: !!session
    spacing: Style.space(14)
    Item {
      width: parent.width
      height: Math.max(sessionTitleBlock.implicitHeight, detailInclusionControl.implicitHeight)
      Column {
        id: sessionTitleBlock
        width: Math.max(0, parent.width - detailInclusionControl.width - Style.space(12))
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.spacing.labelGap
        Text {
          width: parent.width
          text: detailView.session ? root.sessionTitle(detailView.session.config)
            + " · " + Qt.formatDateTime(new Date(detailView.session.start.utcMs), "ddd, MMM d, yyyy")
            + (detailView.session.status === "stopped" ? " · Stopped" : "") : ""
          textFormat: Text.PlainText
          color: root.foreground
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          font.weight: Font.Medium
          wrapMode: Text.WordWrap
        }
        Text {
          width: parent.width
          text: {
            if (!detailView.session) return ""
            var start = new Date(detailView.session.start.utcMs)
            var end = new Date(detailView.session.end.utcMs)
            var sameDay = Qt.formatDateTime(start, "yyyy-MM-dd") === Qt.formatDateTime(end, "yyyy-MM-dd")
            return Qt.formatDateTime(start, "HH:mm:ss") + " → " + Qt.formatDateTime(end, sameDay ? "HH:mm:ss" : "MMM d, yyyy HH:mm:ss")
          }
          HoverHelp { helpText: root.timeRange(detailView.session) }
          color: root.foreground
          opacity: 0.6
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }
      }
      Column {
        id: detailInclusionControl
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(detailInclusion.implicitWidth, detailInclusionLabel.implicitWidth)
        spacing: Style.space(2)
        ToggleSwitch {
          id: detailInclusion
          objectName: "plancks_sessionDetailToggle"
          anchors.horizontalCenter: parent.horizontalCenter
          trackHeight: Style.space(16)
          cursorPad: Style.space(4)
          checked: !!detailView.session && !detailView.session.invalid && !detailView.session.excludedFromStatistics
          enabled: !!detailView.session && !detailView.session.invalid && EpochController.ready
            && !EpochController.busy && !EpochController.sessionHistoryLoading
          foreground: root.foreground
          activeFocusOnTab: true
          hasCursor: activeFocus
          Accessible.role: Accessible.CheckBox
          Accessible.name: "Use session for statistics"
          Accessible.description: detailView.session && detailView.session.invalid ? "Excluded: clock changed" : checked ? "Included" : "Excluded"
          Accessible.checkable: true
          Accessible.checked: checked
          onActiveFocusChanged: if (activeFocus) root.revealRequested(detailInclusionControl)
          Keys.onSpacePressed: if (enabled) toggled()
          Keys.onReturnPressed: if (enabled) toggled()
          Keys.onEnterPressed: if (enabled) toggled()
          onToggled: {
            if (!enabled) return
            forceActiveFocus()
            EpochController.setSessionInclusion(detailView.session.sessionId, checked)
          }
          PanelToolTip {
            visible: root.tooltipsEnabled && detailInclusion.containsMouse
            text: "Use for statistics · " + (detailView.session && detailView.session.invalid ? "Excluded: clock changed" : detailInclusion.checked ? "Included" : "Excluded")
            fontFamily: root.fontFamily
          }
        }
        Text {
          id: detailInclusionLabel
          anchors.horizontalCenter: parent.horizontalCenter
          text: detailInclusion.checked ? "Included" : "Excluded"
          color: root.foreground
          opacity: detailInclusion.checked ? 0.75 : 0.55
          font.family: root.fontFamily
          font.pixelSize: Style.font.caption
        }
      }
    }
    PanelSeparator { foreground: root.foreground }
    PanelSectionHeader { width: parent.width; text: "SAVED SETTINGS"; foreground: root.foreground; fontFamily: root.fontFamily }
    DetailValues {
      width: parent.width
      entries: {
        if (!detailView.session) return []
        var c = detailView.session.config
        return [["Activity", c.focusMinutes + "m"], ["Rest", c.shortBreakMinutes + "m"],
          ["Long rest", c.longBreakEnabled ? c.longBreakMinutes + "m / " + c.longBreakEvery : "Off",
            c.longBreakEnabled ? c.longBreakMinutes + " minutes every " + c.longBreakEvery + " activity rounds" : "Off"],
          ["Final rest", c.finalBreak ? "Included" : "None"],
          ["Parent epoch", root.stamp(detailView.session.epochStart.utcMs),
            root.fullStamp(detailView.session.epochStart.utcMs)]]
      }
    }
    PanelSeparator { foreground: root.foreground }
    PanelSectionHeader { width: parent.width; text: "SESSION TOTALS"; foreground: root.foreground; fontFamily: root.fontFamily }
    DetailValues {
      objectName: "plancks_sessionDetailTotals"
      width: parent.width
      entries: detailView.session ? [
        root.durationRecord("Completed activity", detailView.session.completedFocusMs),
        root.durationRecord("Partial activity", detailView.session.partialFocusMs),
        root.durationRecord("Rest", detailView.session.breakMs),
        root.durationRecord("Paused", detailView.session.pausedMs),
        ["Completed rounds", detailView.session.completedRounds + " / " + detailView.session.config.rounds]
      ] : []
    }
    Text {
      width: parent.width
      visible: !!detailView.session && (detailView.session.invalid || detailView.session.reason === "epoch-ended")
      text: detailView.session && detailView.session.invalid ? "Clock changed · invalid times excluded" : "Stopped when the parent epoch ended"
      color: root.foreground
      opacity: 0.6
      font.family: root.fontFamily
      font.pixelSize: Style.font.caption
      wrapMode: Text.WordWrap
    }
    PanelSeparator { foreground: root.foreground }
    PanelSectionHeader { id: stageHeading; objectName: "plancks_stageHeading"; width: parent.width; text: "STAGES"; foreground: root.foreground; fontFamily: root.fontFamily }
    Column {
      width: parent.width
      spacing: Style.space(8)
      Repeater {
        objectName: "plancks_stageRows"
        model: detailView.session ? detailView.session.stages.slice(detailView.stagePage * 4, (detailView.stagePage + 1) * 4) : []
        delegate: Column {
          id: stageRow
          required property var modelData
          required property int index
          width: parent.width
          spacing: Style.space(6)
          PanelSeparator { visible: stageRow.index > 0; foreground: root.foreground }
          Item {
            width: parent.width
            height: Math.max(stageTitle.implicitHeight, stageOutcome.implicitHeight)
            Text {
              id: stageTitle
              width: Math.max(0, parent.width - stageOutcome.width - Style.space(12))
              text: ({focus: "Activity", short_break: "Rest", long_break: "Long rest"})[stageRow.modelData.kind] + " · Round " + stageRow.modelData.round
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
              font.weight: Font.Medium
              wrapMode: Text.WordWrap
            }
            Text {
              id: stageOutcome
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              text: stageRow.modelData.invalid ? "Clock changed" : stageRow.modelData.outcome === "completed" ? "Completed" : stageRow.modelData.outcome === "stopped" ? "Stopped" : "Not started"
              color: root.foreground
              opacity: 0.6
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
          }
          DetailValues {
            width: parent.width
            entries: {
              var s = stageRow.modelData
              var rows = [root.durationRecord("Planned", s.plannedMs)]
              if (s.actualMs !== undefined) rows.push(
                root.durationRecord("Actual", s.actualMs),
                ["Difference", (s.differenceMs < 0 ? "−" : "+") + root.compactLength(s.differenceMs),
                  (s.differenceMs < 0 ? "−" : "+") + root.length(Math.abs(s.differenceMs)),
                  "Actual minus planned duration. Overrun: " + root.length(s.overrunMs)],
                root.durationRecord("Paused", s.pausedMs))
              return rows
            }
          }
        }
      }
    }
    PanelSeparator { visible: detailView.stagePages > 1; foreground: root.foreground }
    Item {
      id: stagePagination
      visible: detailView.stagePages > 1
      width: parent.width
      readonly property real navigationWidth: Math.max(previousStagePage.implicitWidth, nextStagePage.implicitWidth)
      implicitHeight: Math.max(previousStagePage.implicitHeight, nextStagePage.implicitHeight, stagePageLabel.implicitHeight)
      height: implicitHeight
      Button {
        id: previousStagePage
        width: stagePagination.navigationWidth
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        objectName: "plancks_stagesPrevious"
        text: "Previous"
        foreground: root.foreground
        fontFamily: root.fontFamily
        fontSize: Style.font.bodySmall
        horizontalPadding: Style.space(8)
        bordered: enabled
        focusable: enabled
        opacity: enabled ? 1 : 0.35
        enabled: detailView.stagePage > 0
        onActiveFocusChanged: if (activeFocus) root.revealRequested(previousStagePage)
        onClicked: if (enabled) detailView.changeStagePage(detailView.stagePage - 1)
      }
      Text {
        id: stagePageLabel
        objectName: "plancks_stagesPageLabel"
        width: Math.max(0, parent.width - stagePagination.navigationWidth * 2 - Style.space(16))
        anchors.centerIn: parent
        text: "Page " + (detailView.stagePage + 1) + " of " + detailView.stagePages
        textFormat: Text.PlainText
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        color: root.foreground
        opacity: 0.6
        font.family: root.fontFamily
        font.pixelSize: Style.font.bodySmall
      }
      Button {
        id: nextStagePage
        width: stagePagination.navigationWidth
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        objectName: "plancks_stagesNext"
        text: "Next"
        foreground: root.foreground
        fontFamily: root.fontFamily
        fontSize: Style.font.bodySmall
        horizontalPadding: Style.space(8)
        bordered: enabled
        focusable: enabled
        opacity: enabled ? 1 : 0.35
        enabled: detailView.stagePage + 1 < detailView.stagePages
        onActiveFocusChanged: if (activeFocus) root.revealRequested(nextStagePage)
        onClicked: if (enabled) detailView.changeStagePage(detailView.stagePage + 1)
        KeyNavigation.tab: root.backControl
      }
    }
    }
  }
}
