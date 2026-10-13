import QtQuick
import qs.Commons
import qs.Ui
import "."

Column {
  id: root
  property var backControl: null
  property bool tooltipsEnabled: true
  property string fontFamily: Style.font.family
  signal pageChanged()
  function changePage(page) {
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
  function sessionTitle(config) { return config.name ? config.name + " · Custom" : config.preset === "pomodoro" ? "Pomodoro" : "Custom" }
  function stamp(ms) { return Qt.formatDateTime(new Date(ms), "ddd, MMM d yyyy HH:mm") }
  onVisibleChanged: if (visible) { search.text = ""; delay.stop(); EpochController.requestSessionHistory(0, "") } else { detail = null; focusSessionId = ""; delay.stop() }
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
    HistoryTrend {
      id: focusTrend
      objectName: "plancks_sessionFocusTrend"
      width: parent.width
      title: "Activity time"
      sessionTrend: true
      points: root.history.trend || []
      foreground: root.foreground
      fontFamily: root.fontFamily
      tooltipsEnabled: root.tooltipsEnabled
    }
    Text {
      width: parent.width
      visible: focusTrend.points.length > 0 && !!root.history.query
      text: "Latest sessions · unaffected by search"
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
  BoundedTextField {
    id: search
    objectName: "plancks_sessionSearch"
    width: parent.width; visible: !root.detail; placeholderText: "Search names, dates, presets…"
    foreground: root.foreground; maximumLength: 256
    font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
    Accessible.name: "Search sessions"
    onTextChanged: if (root.visible) delay.restart()
    onAccepted: { delay.stop(); EpochController.requestSessionHistory(0, text) }
    Keys.onEscapePressed: { if (text.length) { text = ""; delay.stop(); EpochController.requestSessionHistory(0, "") } else root.backRequested() }
    onActiveFocusChanged: if (activeFocus) root.revealRequested(search)
  }
  Timer { id: delay; interval: 250; onTriggered: EpochController.requestSessionHistory(0, search.text) }
  Text { width: parent.width; visible: !root.detail && (EpochController.sessionHistoryError.length > 0 || EpochController.error.length > 0 || root.history.total === 0)
    text: EpochController.sessionHistoryError || EpochController.error || (EpochController.sessionHistoryLoading ? "Loading sessions…" : "No matching sessions.")
    color: root.foreground; font.pixelSize: Style.font.bodySmall; wrapMode: Text.WordWrap }
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
              foreground: root.foreground
              fontFamily: root.fontFamily
              fontSize: Style.font.caption
              horizontalPadding: Style.space(8)
              verticalPadding: Style.space(2)
              focusable: true
              bordered: true
              Accessible.name: "View session: " + rowTitle.text
              Accessible.description: rowTiming.text + ", " + sessionRow.modelData.status
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
  component DetailValues: Column {
    id: values
    property var entries: []
    spacing: Style.space(6)
    Repeater {
      model: values.entries
      delegate: Item {
        required property var modelData
        width: values.width
        implicitHeight: Math.max(label.implicitHeight, value.implicitHeight)
        height: implicitHeight
        Text {
          id: label
          width: parent.width * 0.45
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
          width: parent.width * 0.55 - Style.space(12)
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
  Column {
    id: detailView
    objectName: "plancks_sessionDetailSummary"
    readonly property var session: root.detail
    width: parent.width
    visible: !!session
    spacing: Style.space(14)
    Column {
      width: parent.width
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
        color: root.foreground
        opacity: 0.6
        font.family: root.fontFamily
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.WordWrap
      }
    }
    PanelSeparator { foreground: root.foreground }
    PanelSectionHeader { width: parent.width; text: "SESSION TOTALS"; foreground: root.foreground; fontFamily: root.fontFamily }
    DetailValues {
      objectName: "plancks_sessionDetailTotals"
      width: parent.width
      entries: detailView.session ? [
        ["Completed rounds", detailView.session.completedRounds + " / " + detailView.session.config.rounds],
        ["Completed activity", root.length(detailView.session.completedFocusMs)],
        ["Partial activity", root.length(detailView.session.partialFocusMs)],
        ["Rest", root.length(detailView.session.breakMs)],
        ["Paused", root.length(detailView.session.pausedMs)]
      ] : []
    }
    Item {
      width: parent.width
      height: Math.max(statisticsLabel.implicitHeight, detailInclusionControl.implicitHeight)
      Text {
        id: statisticsLabel
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        text: "Statistics"
        color: root.foreground
        opacity: 0.6
        font.family: root.fontFamily
        font.pixelSize: Style.font.bodySmall
      }
      Column {
        id: detailInclusionControl
        anchors.right: parent.right
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
    PanelSectionHeader { width: parent.width; text: "STAGES"; foreground: root.foreground; fontFamily: root.fontFamily }
    Column {
      width: parent.width
      spacing: Style.space(8)
      Repeater {
        model: detailView.session ? detailView.session.stages : []
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
              var rows = [["Planned", root.length(s.plannedMs)]]
              if (s.actualMs !== undefined) rows.push(
                ["Actual", root.length(s.actualMs)],
                ["Difference", (s.differenceMs < 0 ? "−" : s.differenceMs > 0 ? "+" : "") + root.length(Math.abs(s.differenceMs))],
                ["Overrun", root.length(s.overrunMs)],
                ["Paused", root.length(s.pausedMs)])
              return rows
            }
          }
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
          ["Long rest", c.longBreakEnabled ? c.longBreakMinutes + "m every " + c.longBreakEvery + " rounds" : "Off"],
          ["Final rest", c.finalBreak ? "Included" : "None"],
          ["Parent epoch", root.stamp(detailView.session.epochStart.utcMs)]]
      }
    }
  }
}
