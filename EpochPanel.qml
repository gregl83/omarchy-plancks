import QtQuick
import qs.Commons
import qs.Ui
import "."
import "Graphics.js" as Graphics

Panel {
  id: root
  objectName: "plancks_root"
  moduleName: "gregl83.plancks"
  manageIpc: false
  property var anchorItem: null
  property var hostWidget: null
  readonly property bool tooltipsEnabled: !hostWidget || hostWidget.tooltipsEnabled
  readonly property var epoch: EpochController.state
  property bool showingSettings: false
  function openSettings() {
    keys.forceActiveFocus()
    showingHistory = false
    showingSettings = true
    Qt.callLater(function() { scroll.contentY = 0; keys.forceActiveFocus() })
  }
  function closeSettings() {
    keys.forceActiveFocus()
    confirmingReset = false
    showingSettings = false
    Qt.callLater(function() { scroll.contentY = 0; keys.forceActiveFocus() })
  }
  property bool showingHistory: false
  function openHistory() {
    showingSettings = false
    showingHistory = true
    EpochController.requestHistory(0)
    Qt.callLater(function() { scroll.contentY = 0; keys.forceActiveFocus() })
  }
  function closeHistory() {
    keys.forceActiveFocus()
    showingHistory = false
    Qt.callLater(function() { scroll.contentY = 0; keys.forceActiveFocus() })
  }
  property var historyLink: null
  property bool confirmingReset: false
  property string resetGeneration: ""
  property int resetSequence: 0
  function cancelReset() {
    keys.forceActiveFocus()
    confirmingReset = false
    resetButton.forceActiveFocus()
  }
  function revealButton(button) {
    Qt.callLater(function() {
      // A history refresh may replace a focused row before this runs.
      if (!button || typeof button.mapToItem !== "function" || !button.visible) return
      var top = button.mapToItem(scroll.contentItem, 0, 0).y
      var bottom = top + button.height
      if (top < scroll.contentY) scroll.contentY = top
      else if (bottom > scroll.contentY + scroll.height) scroll.contentY = bottom - scroll.height
    })
  }
  property bool detailSubscription: false
  onOpenedChanged: {
    confirmingReset = false
    showingHistory = false
    showingSettings = false
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
  readonly property string samplesExplanation: "Counts are epoch / off-time. Each prediction uses up to five recent completed, included intervals of that kind. Excluded intervals do not count."

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
    if (row.format === "elapsed" && root.epoch.lastStartUtcMs == null)
      return compact ? "—" : "Not started yet"
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
      onCloseRequested: { if (root.showingHistory) root.closeHistory(); else if (root.confirmingReset) root.cancelReset(); else if (root.showingSettings) root.closeSettings(); else root.close() }
      onTabRequested: function(direction) {
        if (root.showingHistory) historyView.focusBack()
        else if (root.confirmingReset) cancelButton.forceActiveFocus()
        else if (root.showingSettings) tooltipSwitch.forceActiveFocus()
        else if (actionButton.enabled) actionButton.forceActiveFocus()
        else if (retryButton.visible) retryButton.forceActiveFocus()
      }
      onMoveRequested: function(dx, dy) { scroll.contentY = Math.max(0, Math.min(scroll.contentHeight - scroll.height, scroll.contentY + dy * Style.space(48))) }
      onActivateRequested: {
        if (root.showingHistory) historyView.focusBack()
        else if (root.confirmingReset) root.cancelReset()
        else if (root.showingSettings) historyBackButton.forceActiveFocus()
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
            implicitHeight: Math.max(title.implicitHeight, phaseBadge.implicitHeight)
            height: implicitHeight

            Text {
              id: title
              anchors.left: parent.left
              anchors.verticalCenter: parent.verticalCenter
              text: "Plancks"
              textFormat: Text.PlainText
              color: subview && !activeFocus && !titleMouse.containsMouse
                ? Qt.darker(root.foreground, 1.4) : root.foreground
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.title
              font.bold: true
              readonly property bool subview: root.showingHistory || root.showingSettings || root.confirmingReset
              activeFocusOnTab: subview
              Accessible.role: subview ? Accessible.Link : Accessible.StaticText
              Accessible.name: subview ? "Plancks: return to current epoch" : "Plancks"
              function returnToMain() {
                if (root.showingHistory) root.closeHistory()
                else if (root.showingSettings) root.closeSettings()
              }
              Keys.onReturnPressed: if (subview) returnToMain()
              Keys.onEnterPressed: if (subview) returnToMain()
              Keys.onSpacePressed: if (subview) returnToMain()
              Keys.onEscapePressed: if (subview) returnToMain(); else root.close()
              onActiveFocusChanged: if (activeFocus) root.revealButton(title)
              MouseArea {
                id: titleMouse
                anchors.fill: parent
                visible: title.subview
                enabled: title.subview
                hoverEnabled: title.subview
                cursorShape: title.subview ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: if (title.subview) title.returnToMain()
              }
            }
            Row {
              id: breadcrumb
              anchors.left: title.right
              anchors.leftMargin: Style.space(6)
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(6)
              visible: title.subview
              Text {
                id: breadcrumbSeparator
                text: "›"
                color: root.foreground
                opacity: 0.4
                font.family: title.font.family
                font.pixelSize: title.font.pixelSize
              }
              Text {
                objectName: "plancks_pageTitle"
                width: Math.min(implicitWidth, Math.max(0, header.width - Math.max(phaseBadge.implicitWidth, historyBackButton.implicitWidth) - breadcrumb.x - breadcrumbSeparator.width - breadcrumb.spacing - Style.space(12)))
                text: root.showingHistory ? "History" : root.confirmingReset ? "Reset" : "Settings"
                textFormat: Text.PlainText
                color: root.foreground
                font.family: title.font.family
                font.pixelSize: title.font.pixelSize
                font.bold: true
                elide: Text.ElideRight
              }
            }
            Text {
              id: phaseBadge
              visible: !title.subview
              anchors.right: settingsButton.left
              anchors.rightMargin: Style.space(8)
              anchors.verticalCenter: parent.verticalCenter
              text: root.epoch.phase === "active" ? "● ACTIVE" : "○ OFF-TIME"
              textFormat: Text.PlainText
              color: root.foreground
              opacity: 0.6
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Math.max(Style.space(9), Style.font.caption - Style.space(1))
              Accessible.name: root.epoch.phase === "active" ? "Epoch active" : "Off-time"
            }
            Button {
              id: settingsButton
              objectName: "plancks_settingsButton"
              visible: !title.subview
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              iconText: "\uf013"
              iconSize: Style.font.bodySmall
              Accessible.role: Accessible.Button
              Accessible.name: "Settings"
              Accessible.description: "Tooltips and data settings."
              tooltipText: root.tooltipsEnabled ? "Settings" : ""
              foreground: Qt.darker(root.foreground, 1.4)
              fontFamily: title.font.family
              fontSize: Style.font.caption
              horizontalPadding: Style.space(4)
              verticalPadding: Style.space(2)
              focusable: true
              bordered: false
              KeyNavigation.backtab: retryButton.visible ? retryButton : root.historyLink
              KeyNavigation.tab: actionButton.enabled ? actionButton : retryButton
              onActiveFocusChanged: if (activeFocus) root.revealButton(settingsButton)
              onClicked: root.openSettings()
              Keys.onEscapePressed: root.close()
            }
            Button {
              id: historyBackButton
              objectName: "plancks_historyBackButton"
              visible: title.subview
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              text: "Back"
              tooltipText: root.tooltipsEnabled ? (root.confirmingReset ? "Return to settings." : "Return to the current epoch.") : ""
              foreground: Qt.darker(root.foreground, 1.4)
              fontFamily: title.font.family
              fontSize: Style.font.caption
              horizontalPadding: Style.space(4)
              verticalPadding: Style.space(2)
              bordered: false
              focusable: true
              onClicked: {
                if (root.showingHistory) root.closeHistory()
                else if (root.confirmingReset) root.cancelReset()
                else root.closeSettings()
              }
              onActiveFocusChanged: if (activeFocus) root.revealButton(historyBackButton)
              Keys.onEscapePressed: clicked()
            }
          }
          PanelSeparator {
            foreground: root.foreground
          }
          Column {
            id: normalContent
            width: parent.width
            spacing: Style.space(14)
            visible: !root.confirmingReset && !root.showingHistory && !root.showingSettings
            Item {
              width: parent.width
              height: Math.max(coffee.height, timerText.implicitHeight + Style.space(20))
              Accessible.role: Accessible.StaticText
              Accessible.name: "Plancks. " + root.epoch.timer + ". " + root.epoch.status
              Item {
                id: timerFrame
                // Allow for the drawing's inset, with about 16 px after the handle.
                readonly property real leftInset: coffee.width - Style.space(4)
                x: leftInset
                width: Math.max(0, parent.width - leftInset)
                height: parent.height
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
              Item {
                id: coffee
                objectName: "plancks_coffee"
                width: Style.space(58)
                height: Style.space(54)
                anchors.left: parent.left
                anchors.leftMargin: -Style.space(5)
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -Style.space(3)
                opacity: timerText.opacity
                function seconds(value) {
                  var parts = String(value).replace(/^[+−-]/, "").split(":")
                  if (parts.length !== 3 || parts.some(function(p) { return !/^\d+$/.test(p) })) return NaN
                  return Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2])
                }
                readonly property real elapsedSeconds: seconds(root.epoch.elapsed)
                readonly property real timerSeconds: seconds(timerText.timer)
                readonly property bool predicted: (root.epoch.phase === "active"
                  ? root.epoch.predictedEndUtcMs : root.epoch.predictedStartUtcMs) !== null
                  && isFinite(timerSeconds) && isFinite(elapsedSeconds)
                readonly property real remainingSeconds: timerText.countingDown ? timerSeconds : -timerSeconds
                // Derive the anchored duration from elapsed + remaining, rather
                // than a learned average that may change during this interval.
                readonly property real durationSeconds: Math.max(1, elapsedSeconds + remainingSeconds)
                readonly property real remainingFraction: Math.max(0, Math.min(1, remainingSeconds / durationSeconds))
                // Epochs consume the cup; off-time replenishes it.
                readonly property real fill: predicted
                  ? root.epoch.phase === "active" ? remainingFraction : 1 - remainingFraction
                  : 0
                readonly property bool overtime: predicted && remainingSeconds < 0
                readonly property bool learning: !predicted && isFinite(timerSeconds)
                AnimatedGraphic {
                  objectName: "plancks_timerGraphic"
                  anchors.fill: parent
                  graphic: root.hostWidget ? root.hostWidget.animatedGraphic : "coffee"
                  foreground: root.foreground
                  fill: coffee.fill
                  learning: coffee.learning
                  phase: root.epoch.phase
                  overtime: coffee.overtime
                  animated: normalContent.visible && root.opened
                }

              }
              Text {
                id: timerText
                anchors.centerIn: timerFrame
                readonly property string timer: root.epoch.timer || "--:--:--"
                readonly property bool countingDown: /^[−-]/.test(timer)
                textFormat: Text.RichText
                text: "<span style=\"font-size: " + Style.space(20) + "px;\"><i>t</i><sub>P</sub></span> " + timer
                color: root.foreground
                opacity: root.epoch.phase !== "active" && EpochController.error === "" ? 0.45 : 1
                Behavior on opacity {
                  NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                }
                font.family: Style.font.family
                font.pixelSize: Style.space(32)
                scale: Math.min(1, Math.max(0, timerFrame.width - Style.space(32)) / implicitWidth)
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
                visible: root.tooltipsEnabled && captionHover.containsMouse
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
                property string helpText: root.epoch.phase === "active"
                  ? "End now; learn from this epoch."
                  : "Start now; learn from the off-time."
                tooltipText: root.tooltipsEnabled ? helpText : ""
                iconText: root.epoch.phase === "active" ? "\uDB81\uDCDB" : "\uDB81\uDC0A"
                enabled: EpochController.ready && !EpochController.busy && !root.confirmingReset
                focusable: true
                bordered: true
                foreground: root.foreground
                background: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.04)
                Accessible.role: Accessible.Button
                Accessible.name: text
                Accessible.description: helpText
                onClicked: if (enabled) EpochController.transition()
                Keys.onEscapePressed: root.close()
              }
              Button {
                id: skipButton
                objectName: "plancks_skipButton"
                onActiveFocusChanged: if (activeFocus) root.revealButton(skipButton)
                KeyNavigation.tab: root.historyLink
                KeyNavigation.backtab: actionButton
                width: actionButton.width
                fontSize: Style.font.bodySmall
                horizontalPadding: Style.space(8)
                text: root.epoch.phase === "active" ? "Skip to end epoch" : "Skip to start epoch"
                iconText: "\uDB81\uDCAD"
                property string helpText: root.epoch.phase === "active"
                  ? "End now; exclude this epoch from predictions."
                  : "Start now; exclude the off-time from predictions."
                tooltipText: root.tooltipsEnabled ? helpText : ""
                enabled: actionButton.enabled
                focusable: true
                bordered: true
                foreground: root.foreground
                Accessible.role: Accessible.Button
                Accessible.name: text
                Accessible.description: helpText
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
                      id: detailCell
                      required property var modelData
                      required property int index
                      width: modelData.isValue ? sectionDetails.valueWidth
                        : sectionDetails.columns === 2 ? sectionDetails.labelSpace
                        : index % 4 === 0 ? root.firstLabelWidth : root.secondLabelWidth
                      text: modelData.isValue ? root.detailValue(modelData.row, true) : modelData.row.label
                      readonly property string detailTooltip: root.detailLabel(modelData.row) + ": " + root.detailValue(modelData.row, false)
                        + (modelData.row.format === "samples" ? "\n" + root.samplesExplanation : "")
                      Accessible.name: detailTooltip
                      MouseArea {
                        id: detailHover
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                      }
                      PanelToolTip {
                        id: detailTip
                        visible: root.tooltipsEnabled && detailHover.containsMouse
                        text: detailCell.detailTooltip
                        fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                        contentItem: Column {
                          spacing: Style.space(6)
                          leftPadding: Border.left(detailTip.panelBorderSpec) + Style.spacing.controlPaddingX
                          rightPadding: Border.right(detailTip.panelBorderSpec) + Style.spacing.controlPaddingX
                          topPadding: Border.top(detailTip.panelBorderSpec) + Style.spacing.controlPaddingY
                          bottomPadding: Border.bottom(detailTip.panelBorderSpec) + Style.spacing.controlPaddingY
                          Row {
                            id: tooltipHeading
                            Text {
                              text: root.detailLabel(detailCell.modelData.row) + ": "
                              textFormat: Text.PlainText
                              color: detailTip.panelForeground
                              opacity: 0.55
                              font.family: detailTip.fontFamily
                              font.pixelSize: detailTip.fontSize
                              font.weight: Font.Normal
                            }
                            Text {
                              text: root.detailValue(detailCell.modelData.row, false)
                              textFormat: Text.PlainText
                              color: detailTip.panelForeground
                              font.family: detailTip.fontFamily
                              font.pixelSize: detailTip.fontSize
                              font.weight: Font.Normal
                            }
                          }
                          Text {
                            visible: detailCell.modelData.row.format === "samples"
                            width: tooltipHeading.width
                            text: root.samplesExplanation
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                            color: detailTip.panelForeground
                            font.family: detailTip.fontFamily
                            font.pixelSize: detailTip.fontSize
                          }
                        }
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

                Button {
                  id: historyButton
                  objectName: "plancks_historyButton"
                  visible: sectionGroup.modelData.section === "History"
                  anchors.horizontalCenter: parent.horizontalCenter
                  text: "View history"
                  property string helpText: "Review recorded intervals and choose which to use for predictions."
                  tooltipText: root.tooltipsEnabled ? helpText : ""
                  fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                  fontSize: Style.font.caption
                  horizontalPadding: Style.space(4)
                  verticalPadding: Style.space(2)
                  foreground: Qt.darker(root.foreground, 1.4)
                  focusable: true
                  bordered: false
                  KeyNavigation.tab: retryButton.visible ? retryButton : settingsButton
                  KeyNavigation.backtab: skipButton
                  Component.onCompleted: if (sectionGroup.modelData.section === "History") root.historyLink = historyButton
                  onActiveFocusChanged: if (activeFocus) root.revealButton(historyButton)
                  onClicked: root.openHistory()
                  Keys.onEscapePressed: root.close()
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
              KeyNavigation.tab: settingsButton
              visible: EpochController.error !== ""
              text: "Retry"
              property string helpText: "Retry the pending action or reconnect to storage."
              tooltipText: root.tooltipsEnabled ? helpText : ""
              enabled: !EpochController.busy && !root.confirmingReset
              focusable: true
              bordered: true
              foreground: root.foreground
              onClicked: if (enabled) EpochController.retry()
              Keys.onEscapePressed: root.close()
            }


          }
          Column {
            id: settingsView
            objectName: "plancks_settingsView"
            width: parent.width
            spacing: Style.space(14)
            visible: root.showingSettings && !root.confirmingReset
            property int previewElapsed: 0
            onVisibleChanged: if (!visible) previewElapsed = 0
            Timer {
              objectName: "plancks_graphicPreviewTimer"
              interval: 100
              repeat: true
              running: root.opened && settingsView.visible
              onTriggered: settingsView.previewElapsed = (settingsView.previewElapsed + interval * 0.55) % 17200
            }
            Item {
              id: tooltipControl
              width: parent.width
              height: Math.max(tooltipLabel.implicitHeight, tooltipSwitch.implicitHeight)
              Text {
                id: tooltipLabel
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Tooltips"
                color: root.foreground
                font.family: title.font.family
                font.pixelSize: Style.font.bodySmall
              }
              ToggleSwitch {
                id: tooltipSwitch
                objectName: "plancks_tooltipsSwitch"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                trackHeight: Style.space(16)
                cursorPad: Style.space(4)
                checked: root.tooltipsEnabled
                foreground: root.foreground
                activeFocusOnTab: true
                hasCursor: activeFocus
                Accessible.role: Accessible.CheckBox
                Accessible.name: "Show tooltips"
                Accessible.checkable: true
                Accessible.checked: checked
                KeyNavigation.tab: graphicChoices.itemAt(0)
                KeyNavigation.backtab: historyBackButton
                onActiveFocusChanged: if (activeFocus) root.revealButton(tooltipControl)
                onToggled: {
                  forceActiveFocus()
                  if (root.hostWidget) root.hostWidget.setTooltipsEnabled(!checked)
                }
                Keys.onSpacePressed: toggled()
                Keys.onReturnPressed: toggled()
                Keys.onEnterPressed: toggled()
                Keys.onEscapePressed: root.closeSettings()
              }
            }
            Text {
              width: parent.width
              text: "Show hover hints in the bar and panels."
              wrapMode: Text.WordWrap
              color: root.foreground
              opacity: 0.6
              font.family: title.font.family
              font.pixelSize: Style.font.caption
            }
            PanelSeparator { foreground: root.foreground }
            Column {
              width: parent.width
              spacing: Style.space(8)
              PanelSectionHeader {
                text: "ANIMATED GRAPHIC"
                foreground: root.foreground
                fontFamily: title.font.family
              }
              Text {
                objectName: "plancks_graphicPreviewState"
                width: parent.width
                text: Graphics.previewFrame(settingsView.previewElapsed).state.label
                horizontalAlignment: Text.AlignHCenter
                color: root.foreground
                opacity: 0.6
                font.family: title.font.family
                font.pixelSize: Style.font.caption
              }
              Grid {
                id: graphicGrid
                width: parent.width
                columns: 2
                spacing: Style.space(12)
                Repeater {
                  id: graphicChoices
                  model: Graphics.options
                  delegate: Button {
                    id: graphicChoice
                    required property var modelData
                    required property int index
                    width: (graphicGrid.width - graphicGrid.spacing) / 2
                    implicitHeight: graphicTile.implicitHeight + Style.space(16)
                    objectName: "plancks_graphic_" + modelData.id
                    selected: (root.hostWidget ? root.hostWidget.animatedGraphic : "coffee") === modelData.id
                    // Selection stays visible while the shared button paints its focus border.
                    color: selected ? Style.selectedFillFor(foreground, accent)
                      : activeFocus ? Style.focusFillFor(foreground, accent)
                      : hot ? Style.hoverFillFor(foreground, accent) : background
                    // A selection is restored state, not a hover transition.
                    Behavior on color { enabled: false }
                    foreground: root.foreground
                    bordered: true
                    focusable: true
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: modelData.name
                    Accessible.checkable: true
                    Accessible.checked: selected
                    Accessible.description: "Preview cycles through ready, learning, countdown, and overrun in both phases."
                    KeyNavigation.tab: index + 1 < graphicChoices.count ? graphicChoices.itemAt(index + 1) : insightsSettings.firstControl
                    KeyNavigation.backtab: index > 0 ? graphicChoices.itemAt(index - 1) : tooltipSwitch
                    onClicked: if (root.hostWidget) root.hostWidget.setAnimatedGraphic(modelData.id)
                    onActiveFocusChanged: if (activeFocus) root.revealButton(graphicChoice)
                    Keys.onEscapePressed: root.closeSettings()
                    Column {
                      id: graphicTile
                      width: parent.width - Style.space(16)
                      anchors.centerIn: parent
                      spacing: Style.space(6)
                      GraphicPreview {
                        id: graphicPreview
                        objectName: "plancks_graphicPreview_" + graphicChoice.modelData.id
                        width: Style.space(58)
                        height: Style.space(54)
                        anchors.horizontalCenter: parent.horizontalCenter
                        // Center the drawing's visible bounds, including its handle.
                        anchors.horizontalCenterOffset: Style.space(graphicChoice.modelData.previewOffsetX || 0)
                        graphic: graphicChoice.modelData.id
                        foreground: root.foreground
                        running: root.opened && settingsView.visible
                        elapsed: settingsView.previewElapsed
                      }
                      Text {
                        width: parent.width
                        text: graphicChoice.modelData.name
                        color: root.foreground
                        font.family: title.font.family
                        font.pixelSize: Style.font.bodySmall
                        font.bold: graphicChoice.selected
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                      }
                    }
                  }
                }
              }
            }

            PanelSeparator { foreground: root.foreground }
            InsightsSettings {
              id: insightsSettings
              objectName: "plancks_insightsSettings"
              width: parent.width
              hostWidget: root.hostWidget
              foreground: root.foreground
              fontFamily: title.font.family
              previousControl: graphicChoices.itemAt(graphicChoices.count - 1)
              nextControl: resetButton
              onBackRequested: root.closeSettings()
              onRevealRequested: function(item) { root.revealButton(item) }
            }
            PanelSeparator { foreground: root.foreground }
            Column {
              width: parent.width
              spacing: Style.space(8)
              PanelSectionHeader {
                text: "DATA"
                foreground: root.foreground
                fontFamily: title.font.family
              }
              Text {
                width: parent.width
                text: "Clear recorded history and learned predictions."
                wrapMode: Text.WordWrap
                color: root.foreground
                opacity: 0.6
                font.family: title.font.family
                font.pixelSize: Style.font.caption
              }
              Button {
                id: resetButton
                objectName: "plancks_resetButton"
                text: "Reset all data…"
                tooltipText: root.tooltipsEnabled ? "Review and confirm deletion of all epoch data." : ""
                enabled: !EpochController.busy
                focusable: true
                bordered: true
                fontFamily: title.font.family
                fontSize: Style.font.caption
                height: insightsSettings.previewButtonHeight
                foreground: root.foreground
                KeyNavigation.backtab: insightsSettings.lastControl
                KeyNavigation.tab: historyBackButton
                onActiveFocusChanged: if (activeFocus) root.revealButton(resetButton)
                onClicked: {
                  if (!enabled) return
                  root.resetGeneration = root.epoch.generation
                  root.resetSequence = root.epoch.sequence
                  root.confirmingReset = true
                  cancelButton.forceActiveFocus()
                  Qt.callLater(function() { scroll.contentY = 0 })
                }
                Keys.onEscapePressed: root.closeSettings()
              }
            }
          }
          HistoryView {
            id: historyView
            objectName: "plancks_historyView"
            width: parent.width
            visible: root.showingHistory
            backControl: historyBackButton
            tooltipsEnabled: root.tooltipsEnabled
            foreground: root.foreground
            fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
            onBackRequested: root.closeHistory()
            onRevealRequested: function(item) { root.revealButton(item) }
            onPageChanged: Qt.callLater(function() { scroll.contentY = 0; keys.forceActiveFocus() })
          }
          Column {
            width: parent.width
            spacing: Style.space(14)
            visible: root.confirmingReset
            Text {
              width: parent.width
              text: "Delete recorded epochs, off-time intervals, and learned predictions. Any active epoch will be discarded."
              textFormat: Text.PlainText
              wrapMode: Text.WordWrap
              color: root.foreground
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.bodySmall
            }
            Text {
              width: parent.width
              objectName: "plancks_resetWarning"
              text: "This cannot be undone. Widget settings are kept."
              textFormat: Text.PlainText
              wrapMode: Text.WordWrap
              color: root.foreground
              opacity: 0.6
              font.family: root.bar ? root.bar.fontFamily : Style.font.family
              font.pixelSize: Style.font.bodySmall
            }
            Row {
              width: parent.width
              spacing: Style.space(8)
              Button {
                id: cancelButton
                objectName: "plancks_cancelButton"
                onActiveFocusChanged: if (activeFocus) root.revealButton(cancelButton)
                text: "Cancel"
                property string helpText: "Keep all data and cancel reset."
                tooltipText: root.tooltipsEnabled ? helpText : ""
                width: (parent.width - parent.spacing) / 2
                fontSize: Style.font.bodySmall
                fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                horizontalPadding: Style.space(8)
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
                text: "Delete all data"
                property string helpText: "Permanently delete all epoch data."
                tooltipText: root.tooltipsEnabled ? helpText : ""
                width: cancelButton.width
                fontSize: Style.font.bodySmall
                fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                horizontalPadding: Style.space(8)
                enabled: !EpochController.busy
                focusable: true
                bordered: true
                foreground: root.bar ? root.bar.urgent : Color.urgent
                Accessible.name: text
                Accessible.description: helpText
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
}
