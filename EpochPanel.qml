import QtQuick
import qs.Commons
import qs.Ui
import "."

Panel {
  id: root
  objectName: "plancks_root"
  moduleName: "gregl83.plancks"
  manageIpc: false
  property var anchorItem: null
  property var hostWidget: null
  readonly property var epoch: EpochController.state
  property bool confirmingReset: false
  property string resetGeneration: ""
  property int resetSequence: 0
  function cancelReset() {
    confirmingReset = false
    resetButton.forceActiveFocus()
  }
  function revealButton(button) {
    Qt.callLater(function() {
      var top = button.mapToItem(scroll.contentItem, 0, 0).y
      var bottom = top + button.height
      if (top < scroll.contentY) scroll.contentY = top
      else if (bottom > scroll.contentY + scroll.height) scroll.contentY = bottom - scroll.height
    })
  }
  property bool detailSubscription: false
  onOpenedChanged: {
    confirmingReset = false
    if (detailSubscription !== opened) {
      detailSubscription = opened
      EpochController.setPanelOpen(opened)
    }
  }
  Component.onDestruction: if (detailSubscription) EpochController.setPanelOpen(false)
  readonly property color foreground: bar ? bar.foreground : Color.foreground

  function stamp(value) {
    return value === null || value === undefined ? "Not enough history" : Qt.formatDateTime(new Date(value), "ddd, MMM d, yyyy · HH:mm:ss")
  }
  function length(value) {
    if (value === null || value === undefined) return "Not enough history"
    var seconds = Math.floor(value / 1000)
    return Math.floor(seconds / 3600).toString().padStart(2, "0") + ":"
      + Math.floor(seconds / 60 % 60).toString().padStart(2, "0") + ":"
      + (seconds % 60).toString().padStart(2, "0")
  }

  function compactStamp(value) {
    if (value === null || value === undefined) return "—"
    // Refresh relative dates with the phase's elapsed updates while open.
    var elapsed = root.epoch.elapsed
    var date = new Date(value)
    var today = new Date()
    var days = (Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
      - Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())) / 86400000
    if (days === 0) return "Today " + Qt.formatDateTime(date, "HH:mm")
    if (Math.abs(days) < 7) return Qt.formatDateTime(date, "ddd HH:mm")
    return Qt.formatDateTime(date, date.getFullYear() === today.getFullYear() ? "MMM d HH:mm" : "yyyy-MM-dd HH:mm")
  }
  function compactLength(milliseconds) {
    if (milliseconds === null || milliseconds === undefined) return "—"
    var minutes = Math.floor(milliseconds / 60000)
    if (minutes === 0) return milliseconds > 0 ? "<1m" : "0m"
    var hours = Math.floor(minutes / 60)
    var rest = minutes % 60
    return hours ? hours + "h" + (rest ? " " + rest + "m" : "") : rest + "m"
  }
  function detailLabel(row) {
    if (row.key === "elapsed") return root.epoch.phase === "active" ? "Epoch elapsed" : "Off-time elapsed"
    if (row.key === "predictedEndUtcMs") return root.epoch.phase === "active" ? "Expected epoch end" : "Expected next epoch end"
    return row.description
  }
  function detailValue(row, compact) {
    var value = root.epoch[row.key]
    if (row.format === "samples") {
      if (compact) return root.epoch.workSampleCount + " / " + root.epoch.gapSampleCount
      return root.epoch.workSampleCount + (root.epoch.workSampleCount === 1 ? " epoch · " : " epochs · ")
        + root.epoch.gapSampleCount + (root.epoch.gapSampleCount === 1 ? " off-time interval" : " off-time intervals")
    }
    if (row.format === "stamp") return compact ? compactStamp(value) : value == null && row.empty ? row.empty : stamp(value)
    if (row.format === "length") return compact ? compactLength(value) : length(value)
    if (!compact) return value || "00:00:00"
    var parts = String(value || "00:00:00").split(":")
    return compactLength((Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2])) * 1000)
  }

  FontMetrics {
    id: detailFontMetrics
    font.family: root.bar ? root.bar.fontFamily : Style.font.family
    font.pixelSize: Style.font.bodySmall
  }
  readonly property real firstLabelWidth: Math.ceil(Math.max(
    detailFontMetrics.advanceWidth("End"), detailFontMetrics.advanceWidth("Epoch"),
    detailFontMetrics.advanceWidth("Started"), detailFontMetrics.advanceWidth("Elapsed")))
  readonly property real secondLabelWidth: Math.ceil(Math.max(
    detailFontMetrics.advanceWidth("Next start"), detailFontMetrics.advanceWidth("Off-time"),
    detailFontMetrics.advanceWidth("Ended"), detailFontMetrics.advanceWidth("Samples")))

  KeyboardPanel {
    id: popup
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keys
    contentWidth: fittedContentWidth(Style.space(380))
    contentHeight: fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keys
      objectName: "plancks_keys"
      anchors.fill: parent
      onCloseRequested: { if (root.confirmingReset) root.cancelReset(); else root.close() }
      onTabRequested: function(direction) {
        if (root.confirmingReset) cancelButton.forceActiveFocus()
        else if (actionButton.enabled) actionButton.forceActiveFocus()
        else if (retryButton.visible) retryButton.forceActiveFocus()
      }
      onMoveRequested: function(dx, dy) { scroll.contentY = Math.max(0, Math.min(scroll.contentHeight - scroll.height, scroll.contentY + dy * Style.space(48))) }
      onActivateRequested: {
        if (root.confirmingReset) root.cancelReset()
        else if (EpochController.ready && !EpochController.busy) EpochController.transition()
        else if (EpochController.error && !EpochController.busy) EpochController.retry()
      }
      Flickable {
        id: scroll
        objectName: "plancks_scroll"
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        Column {
          id: column
          width: parent.width
          spacing: Style.space(14)
          Item {
            id: header
            width: parent.width
            readonly property bool stacked: title.implicitWidth + phaseBadge.implicitWidth + Style.space(16) > width
            implicitHeight: stacked
              ? title.height + Style.space(6) + phaseBadge.height
              : Math.max(title.height, phaseBadge.height)
            height: implicitHeight

            Text {
              id: title
              width: Math.min(implicitWidth, header.width)
              y: header.stacked ? 0 : (header.height - height) / 2
              text: "Plancks"
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.title
              font.bold: true
              elide: Text.ElideRight
            }
            Text {
              id: phaseBadge
              x: header.width - width
              y: header.stacked ? title.height + Style.space(6) : (header.height - height) / 2
              width: Math.min(implicitWidth, header.width)
              text: root.epoch.phase === "active" ? "● ACTIVE" : "○ OFF-TIME"
              textFormat: Text.PlainText
              horizontalAlignment: Text.AlignRight
              wrapMode: Text.Wrap
              color: root.foreground
              opacity: 0.6
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Math.max(Style.space(9), Style.font.caption - Style.space(1))
              Accessible.name: root.epoch.phase === "active" ? "Epoch active" : "Off-time"
            }
          }
          PanelSeparator {
            foreground: root.foreground
          }
          Item {
            width: parent.width
            height: timerText.implicitHeight + Style.space(20)
            Item {
              id: timerFrame
              anchors.centerIn: parent
              width: Math.min(parent.width, timerText.implicitWidth + Style.space(32))
              height: parent.height
              Rectangle {
                anchors.fill: parent
                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.03)
              }
              Repeater {
                model: 4
                delegate: Item {
                  required property int index
                  readonly property bool rightSide: index % 2 === 1
                  readonly property bool bottomSide: index >= 2
                  readonly property real lineWidth: Math.max(1, Style.normalBorderWidth)
                  width: Style.space(10)
                  height: Style.space(10)
                  x: rightSide ? timerFrame.width - width : 0
                  y: bottomSide ? timerFrame.height - height : 0
                  opacity: 0.35
                  Rectangle {
                    width: parent.width
                    height: parent.lineWidth
                    y: parent.bottomSide ? parent.height - height : 0
                    color: root.foreground
                  }
                  Rectangle {
                    width: parent.lineWidth
                    height: parent.height
                    x: parent.rightSide ? parent.width - width : 0
                    color: root.foreground
                  }
                }
              }
            }
            Text {
              id: timerText
              anchors.centerIn: parent
              textFormat: Text.RichText
              text: "<span style=\"font-size: " + Style.space(20) + "px;\"><i>t</i><sub>P</sub></span> " + (root.epoch.timer || "--:--:--")
              color: root.foreground
              opacity: root.epoch.phase !== "active" && EpochController.error === "" ? 0.45 : 1
              Behavior on opacity {
                NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
              }
              font.family: Style.font.family
              font.pixelSize: Style.space(32)
            }
          }
          Text {
            width: parent.width
            text: String(root.epoch.status || "")
              .replace(/^(Epoch active|Off-time) · /, "")
              .replace("next epoch start", "start")
              .replace("epoch end", "end")
              .replace(/^(Epoch|Off-time) elapsed · learning your rhythm$/, "Learning your rhythm")
              .replace("Clock changed · prediction unavailable", "Prediction unavailable")
            Accessible.name: root.epoch.status
            MouseArea {
              id: captionHover
              anchors.fill: parent
              hoverEnabled: true
              acceptedButtons: Qt.NoButton
            }
            PanelToolTip {
              visible: captionHover.containsMouse
              text: root.epoch.status
              fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
            }
            textFormat: Text.PlainText
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: root.foreground
            opacity: 0.75
            font.family: Style.font.family
            font.pixelSize: Style.font.bodySmall
          }
          PanelSeparator { foreground: root.foreground }
          Row {
            id: actionRow
            width: parent.width
            spacing: Style.space(8)
            Button {
              id: actionButton
              objectName: "plancks_actionButton"
              onActiveFocusChanged: if (activeFocus) root.revealButton(actionButton)
              KeyNavigation.tab: skipButton
              width: (parent.width - parent.spacing) / 2
              fontSize: Style.font.bodySmall
              horizontalPadding: Style.space(8)
              text: EpochController.busy ? "Saving…" : root.epoch.phase === "active" ? "End epoch" : "Start epoch"
              tooltipText: root.epoch.phase === "active"
                ? "End now; learn from this epoch."
                : "Start now; learn from the off-time."
              iconText: root.epoch.phase === "active" ? "\uDB81\uDCDB" : "\uDB81\uDC0A"
              enabled: EpochController.ready && !EpochController.busy && !root.confirmingReset
              focusable: true
              bordered: true
              foreground: root.foreground
              background: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.04)
              Accessible.role: Accessible.Button
              Accessible.name: text
              Accessible.description: tooltipText
              onClicked: if (enabled) EpochController.transition()
              Keys.onEscapePressed: root.close()
            }
            Button {
              id: skipButton
              objectName: "plancks_skipButton"
              onActiveFocusChanged: if (activeFocus) root.revealButton(skipButton)
              KeyNavigation.tab: retryButton.visible ? retryButton : resetButton
              KeyNavigation.backtab: actionButton
              width: actionButton.width
              fontSize: Style.font.bodySmall
              horizontalPadding: Style.space(8)
              text: root.epoch.phase === "active" ? "Skip to end epoch" : "Skip to start epoch"
              iconText: "\uDB81\uDCAD"
              tooltipText: root.epoch.phase === "active"
                ? "End now; exclude this epoch from predictions."
                : "Start now; exclude the off-time from predictions."
              enabled: actionButton.enabled
              focusable: true
              bordered: true
              foreground: root.foreground
              Accessible.role: Accessible.Button
              Accessible.name: text
              Accessible.description: tooltipText
              onClicked: if (enabled) EpochController.transition(true)
              Keys.onEscapePressed: root.close()
            }
          }
          PanelSeparator { foreground: root.foreground }
          Repeater {
            model: [
              {section: "Predictions", rows: [
                {label: "End", key: "predictedEndUtcMs", format: "stamp"},
                {label: "Next start", description: "Expected next epoch start", key: "predictedStartUtcMs", format: "stamp"},
                {label: "Epoch", description: "Expected epoch duration", key: "workPredictionMs", format: "length"},
                {label: "Off-time", description: "Expected off-time duration", key: "gapPredictionMs", format: "length"}
              ]},
              {section: "History", rows: [
                {label: "Started", description: "Last epoch start", key: "lastStartUtcMs", format: "stamp", empty: "Not started yet"},
                {label: "Ended", description: "Last epoch end", key: "lastEndUtcMs", format: "stamp", empty: "Not ended yet"},
                {label: "Elapsed", key: "elapsed", format: "elapsed"},
                {label: "Samples", description: "Recent samples", key: "workSampleCount", format: "samples"}
              ]}
            ]
            delegate: Column {
              id: sectionGroup
              required property var modelData
              width: column.width
              spacing: Style.space(14)
              PanelSeparator {
                visible: sectionGroup.modelData.section === "History"
                foreground: root.foreground
              }
              PanelSectionHeader {
                width: parent.width
                text: sectionGroup.modelData.section.toUpperCase()
                foreground: root.foreground
                fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
              }
              Grid {
                id: sectionDetails
                objectName: "plancks_" + sectionGroup.modelData.section + "_details"
                width: parent.width
                columns: width >= Style.space(320) ? 4 : 2
                columnSpacing: Style.space(20)
                rowSpacing: Style.spacing.labelGap
                readonly property real labelSpace: columns === 4
                  ? root.firstLabelWidth + root.secondLabelWidth
                  : Math.max(root.firstLabelWidth, root.secondLabelWidth)
                readonly property real valueWidth: Math.max(0,
                  (width - (columns - 1) * columnSpacing - labelSpace) / (columns / 2))
                Repeater {
                  model: {
                    var cells = []
                    for (var row of sectionGroup.modelData.rows) {
                      cells.push({row: row, isValue: false})
                      cells.push({row: row, isValue: true})
                    }
                    return cells
                  }
                  delegate: Text {
                    required property var modelData
                    required property int index
                    width: modelData.isValue ? sectionDetails.valueWidth
                      : sectionDetails.columns === 2 ? sectionDetails.labelSpace
                      : index % 4 === 0 ? root.firstLabelWidth : root.secondLabelWidth
                    text: modelData.isValue ? root.detailValue(modelData.row, true) : modelData.row.label
                    readonly property string detailTooltip: root.detailLabel(modelData.row) + ": " + root.detailValue(modelData.row, false)
                    Accessible.name: detailTooltip
                    MouseArea {
                      id: detailHover
                      anchors.fill: parent
                      hoverEnabled: true
                      acceptedButtons: Qt.NoButton
                    }
                    PanelToolTip {
                      visible: detailHover.containsMouse
                      text: parent.detailTooltip
                      fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                    }
                    textFormat: Text.PlainText
                    horizontalAlignment: modelData.isValue ? Text.AlignRight : Text.AlignLeft
                    wrapMode: modelData.isValue ? Text.WordWrap : Text.NoWrap
                    color: root.foreground
                    opacity: modelData.isValue ? 1 : 0.55
                    font.weight: modelData.isValue ? Font.Medium : Font.Normal
                    font.family: root.bar ? root.bar.fontFamily : Style.font.family
                    font.pixelSize: Style.font.bodySmall
                  }
                }
              }
            }
          }
          Text {
            width: parent.width
            visible: text !== ""
            text: [EpochController.error].concat(root.epoch.warnings || []).filter(function(x) { return !!x }).join("\n")
            wrapMode: Text.WordWrap
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
          }
          Button {
            id: retryButton
            onActiveFocusChanged: if (activeFocus) root.revealButton(retryButton)
            KeyNavigation.tab: resetButton
            visible: EpochController.error !== ""
            text: "Retry"
            tooltipText: "Retry the pending action or reconnect to storage."
            enabled: !EpochController.busy && !root.confirmingReset
            focusable: true
            bordered: true
            foreground: root.foreground
            onClicked: if (enabled) EpochController.retry()
            Keys.onEscapePressed: root.close()
          }
          PanelSeparator { foreground: root.foreground }
          Button {
            id: resetButton
            objectName: "plancks_resetButton"
            onActiveFocusChanged: if (activeFocus) root.revealButton(resetButton)
            anchors.right: parent.right
            text: "Reset all data…"
            tooltipText: "Review and confirm deletion of all epoch data."
            visible: !root.confirmingReset
            enabled: !EpochController.busy
            focusable: true
            bordered: false
            fontSize: Style.font.bodySmall
            foreground: root.foreground
            KeyNavigation.tab: actionButton.enabled ? actionButton : retryButton
            onClicked: {
              if (!enabled) return
              root.resetGeneration = root.epoch.generation
              root.resetSequence = root.epoch.sequence
              root.confirmingReset = true
              cancelButton.forceActiveFocus()
              Qt.callLater(function() { scroll.contentY = Math.max(0, scroll.contentHeight - scroll.height) })
            }
            Keys.onEscapePressed: root.close()
          }
          Column {
            width: parent.width
            spacing: Style.space(10)
            visible: root.confirmingReset
            Text {
              width: parent.width
              objectName: "plancks_resetWarning"
              text: "Reset all Plancks data? This permanently deletes all recorded epochs, off-time intervals, and learned predictions, and discards any active epoch. This cannot be undone. Widget settings are kept."
              textFormat: Text.PlainText
              wrapMode: Text.WordWrap
              color: root.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.body
            }
            Button {
              id: cancelButton
              objectName: "plancks_cancelButton"
              onActiveFocusChanged: if (activeFocus) root.revealButton(cancelButton)
              text: "Cancel"
              tooltipText: "Keep all data and cancel reset."
              width: parent.width
              focusable: true
              bordered: true
              foreground: root.foreground
              KeyNavigation.tab: confirmButton
              KeyNavigation.backtab: confirmButton
              onClicked: root.cancelReset()
              Keys.onEscapePressed: root.cancelReset()
            }
            Button {
              id: confirmButton
              objectName: "plancks_confirmButton"
              onActiveFocusChanged: if (activeFocus) root.revealButton(confirmButton)
              text: "Delete all data and reset"
              tooltipText: "Permanently delete all epoch data."
              width: parent.width
              enabled: !EpochController.busy
              focusable: true
              bordered: true
              foreground: root.foreground
              KeyNavigation.tab: cancelButton
              KeyNavigation.backtab: cancelButton
              onClicked: {
                if (!enabled) return
                root.confirmingReset = false
                EpochController.reset(root.resetGeneration, root.resetSequence)
                keys.forceActiveFocus()
              }
              Keys.onEscapePressed: root.cancelReset()
            }
          }
        }
      }
    }
  }
}
