import QtQuick
import qs.Commons
import qs.Ui
import "."

Panel {
  id: root
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
    return value === null || value === undefined ? "Not enough history" : Qt.formatDateTime(new Date(value), "ddd, MMM d · HH:mm:ss")
  }
  function length(value) {
    if (value === null || value === undefined) return "Not enough history"
    var seconds = Math.floor(value / 1000)
    return Math.floor(seconds / 3600).toString().padStart(2, "0") + ":"
      + Math.floor(seconds / 60 % 60).toString().padStart(2, "0") + ":"
      + (seconds % 60).toString().padStart(2, "0")
  }

  KeyboardPanel {
    id: popup
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keys
    contentWidth: fittedContentWidth(Style.space(420))
    contentHeight: fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keys
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
            readonly property bool stacked: title.implicitWidth + statusMetrics.width + Style.space(16) > width
            implicitHeight: stacked
              ? title.height + Style.space(6) + phaseStatus.height
              : Math.max(title.height, phaseStatus.height)
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
            TextMetrics {
              id: statusMetrics
              font: phaseStatus.font
              text: phaseStatus.text
            }
            Text {
              id: phaseStatus
              x: header.stacked ? 0 : title.width + Style.space(16)
              y: header.stacked ? title.height + Style.space(6) : (header.height - height) / 2
              width: header.stacked ? header.width : Math.max(0, header.width - x)
              text: root.epoch.phase === "active" ? "●  Epoch active" : "○  Off-time"
              textFormat: Text.PlainText
              horizontalAlignment: Text.AlignRight
              wrapMode: Text.Wrap
              color: root.foreground
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
          PanelSeparator {
            foreground: root.foreground
          }
          Text {
            width: parent.width
            textFormat: Text.RichText
            horizontalAlignment: Text.AlignHCenter
            text: "<i>t</i><sub>P</sub> " + (root.epoch.timer || "--:--:--")
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.space(32)
          }
          Text {
            width: parent.width
            text: String(root.epoch.status || "").replace(/^(Epoch active|Off-time) · /, "")
            textFormat: Text.PlainText
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
          }
          Button {
            id: actionButton
            KeyNavigation.tab: retryButton.visible ? retryButton : resetButton
            width: parent.width
            text: EpochController.busy ? "Saving…" : root.epoch.phase === "active" ? "End epoch" : "Start epoch"
            enabled: EpochController.ready && !EpochController.busy && !root.confirmingReset
            focusable: true
            bordered: true
            foreground: root.foreground
            Accessible.role: Accessible.Button
            Accessible.name: text
            onClicked: if (enabled) EpochController.transition()
            Keys.onEscapePressed: root.close()
          }
          Repeater {
            model: [
              {label: "Last epoch start", key: "lastStartUtcMs", format: "stamp", empty: "Not started yet"},
              {label: "Last epoch end", key: "lastEndUtcMs", format: "stamp", empty: "Not ended yet"},
              {label: "", key: "elapsed", format: "elapsed"},
              {label: "Predicted epoch duration", key: "workPredictionMs", format: "length"},
              {label: "Predicted off-time duration", key: "gapPredictionMs", format: "length"},
              {label: "", key: "predictedEndUtcMs", format: "stamp"},
              {label: "Predicted next epoch start", key: "predictedStartUtcMs", format: "stamp"},
              {label: "Recent samples", key: "workSampleCount", format: "samples"}
            ]
            delegate: Column {
              required property var modelData
              width: column.width
              spacing: Style.space(3)
              Text {
                text: {
                  if (parent.modelData.key === "elapsed") return root.epoch.phase === "active" ? "Epoch elapsed" : "Off-time elapsed"
                  if (parent.modelData.key === "predictedEndUtcMs") return root.epoch.phase === "active" ? "Predicted epoch end" : "Predicted next epoch end"
                  return parent.modelData.label
                }
                color: root.foreground
                opacity: 0.65
                font.family: Style.font.family
                font.pixelSize: Style.font.body
              }
              Text {
                width: parent.width
                text: {
                  var row = parent.modelData
                  var value = root.epoch[row.key]
                  if (row.format === "samples") return root.epoch.workSampleCount + (root.epoch.workSampleCount === 1 ? " epoch · " : " epochs · ")
                    + root.epoch.gapSampleCount + (root.epoch.gapSampleCount === 1 ? " off-time interval" : " off-time intervals")
                  if (row.format === "stamp") return value == null && row.empty ? row.empty : root.stamp(value)
                  if (row.format === "length") return root.length(value)
                  return value || "00:00:00"
                }
                wrapMode: Text.WordWrap
                color: root.foreground
                font.family: Style.font.family
                font.pixelSize: Style.font.body
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
            KeyNavigation.tab: resetButton
            visible: EpochController.error !== ""
            text: "Retry"
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
            anchors.right: parent.right
            text: "Reset all data…"
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
              text: "Reset all Plancks data? This permanently deletes all recorded epochs, off-time intervals, and learned predictions, and discards any active epoch. This cannot be undone. Widget settings are kept."
              textFormat: Text.PlainText
              wrapMode: Text.WordWrap
              color: root.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.body
            }
            Button {
              id: cancelButton
              text: "Cancel"
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
              text: "Delete all data and reset"
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
