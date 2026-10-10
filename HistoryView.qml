import QtQuick
import qs.Commons
import qs.Ui
import "."

Column {
  id: root
  spacing: Style.space(14)
  property bool tooltipsEnabled: true
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  property Item backControl: null
  readonly property var history: EpochController.history
  property string focusSampleId: ""
  signal backRequested()
  signal revealRequested(var item)
  signal pageChanged()

  function compactLength(milliseconds) {
    var minutes = Math.floor(milliseconds / 60000)
    if (minutes === 0) return milliseconds > 0 ? "<1m" : "0m"
    var hours = Math.floor(minutes / 60)
    var rest = minutes % 60
    return hours ? hours + "h" + (rest ? " " + rest + "m" : "") : rest + "m"
  }
  function focusBack() { if (backControl) backControl.forceActiveFocus() }
  function searchHistory() {
    searchDelay.stop()
    focusSampleId = ""
    EpochController.requestHistory(0, searchField.text)
  }
  function clearHistorySearch() {
    searchField.text = ""
    searchHistory()
    searchField.forceActiveFocus()
  }
  function changePage(page) {
    focusSampleId = ""
    EpochController.requestHistory(page)
    pageChanged()
  }
  onVisibleChanged: {
    if (!visible) { focusSampleId = ""; searchDelay.stop() }
    else if (searchField.text !== EpochController.historyQuery) searchHistory()
  }
  Timer {
    id: searchDelay
    interval: 250
    onTriggered: root.searchHistory()
  }
  onHistoryChanged: {
    if (!visible || !focusSampleId) return
    Qt.callLater(function() {
      for (var i = 0; i < rows.count; i++) {
        var row = rows.itemAt(i)
        if (row && row.modelData.eventId === root.focusSampleId) {
          row.focusInclusion()
          break
        }
      }
    })
  }
  Keys.onEscapePressed: backRequested()
  Connections {
    target: EpochController.state
    function onSequenceChanged() { if (root.visible) EpochController.requestHistory(EpochController.historyPage) }
    function onGenerationChanged() { if (root.visible) EpochController.requestHistory(0) }
  }
  Connections {
    target: EpochController
    function onBusyChanged() {
      if (root.visible && !EpochController.busy) EpochController.requestHistory(EpochController.historyPage)
    }
  }
  Column {
    width: parent.width
    visible: !!root.history.trends && (root.history.trends.epoch.length > 0 || root.history.trends.off.length > 0)
    spacing: Style.spacing.panelGap
    Column {
      width: parent.width
      spacing: Style.spacing.panelGap
      Row {
        width: parent.width
        spacing: Style.space(20)
        HistoryTrend {
          id: epochTrend
          objectName: "plancks_epochTrend"
          width: offTrend.visible ? (parent.width - parent.spacing) / 2 : parent.width
          tooltipsEnabled: root.tooltipsEnabled
          title: "Epochs"
          points: root.history.trends ? root.history.trends.epoch : []
          foreground: root.foreground
          fontFamily: root.fontFamily
        }
        HistoryTrend {
          id: offTrend
          objectName: "plancks_offTrend"
          width: epochTrend.visible ? (parent.width - parent.spacing) / 2 : parent.width
          tooltipsEnabled: root.tooltipsEnabled
          title: "Off-time"
          points: root.history.trends ? root.history.trends.off : []
          foreground: root.foreground
          fontFamily: root.fontFamily
        }
      }
      Text {
        width: parent.width
        visible: !!root.history.query
        text: "Latest intervals · unaffected by search"
        textFormat: Text.PlainText
        wrapMode: Text.WordWrap
        color: root.foreground
        opacity: 0.6
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
      }
    }
    PanelSeparator { foreground: root.foreground }
  }
  Row {
    width: parent.width
    spacing: Style.space(8)
    TextField {
      id: searchField
      objectName: "plancks_historySearch"
      width: parent.width - (clearSearch.visible ? clearSearch.width + parent.spacing : 0)
      placeholderText: "Search dates, times, durations…"
      // Restore once; live request updates must never replace text being edited.
      Component.onCompleted: text = EpochController.historyQuery
      maximumLength: 256
      foreground: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
      Accessible.name: "Search history"
      onTextChanged: if (root.visible && text !== EpochController.historyQuery) searchDelay.restart()
      onAccepted: root.searchHistory()
      onActiveFocusChanged: if (activeFocus) root.revealRequested(searchField)
      Keys.onEscapePressed: {
        if (text.length > 0) root.clearHistorySearch()
        else root.backRequested()
      }
    }
    Button {
      id: clearSearch
      objectName: "plancks_historyClearSearch"
      anchors.verticalCenter: searchField.verticalCenter
      visible: searchField.text.length > 0
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
  Text {
    width: parent.width
    visible: !!root.history.query
    text: EpochController.historyLoading ? "Searching…"
      : root.history.total + (root.history.total === 1 ? " matching interval" : " matching intervals")
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
  Text {
    width: parent.width
    visible: root.history.total === 0 && EpochController.historyError === ""
    text: EpochController.historyLoading ? "Loading history…"
      : root.history.query ? "No matching intervals." : "No completed intervals yet."
    textFormat: Text.PlainText
    wrapMode: Text.WordWrap
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
  }
  Column {
    width: parent.width
    spacing: Style.space(8)
    Repeater {
      id: rows
      model: root.history.rows
      delegate: Column {
        id: intervalRow
        required property var modelData
        required property int index
        readonly property string sampleStatus: modelData.durationMs < 0 ? "Excluded: clock moved backwards"
          : modelData.excludedFromLearning ? "Excluded"
          : modelData.recent ? "Recent sample" : "Outside the recent sample window"
        function focusInclusion() { inclusion.forceActiveFocus() }
        width: root.width
        spacing: Style.space(6)
        PanelSeparator {
          visible: intervalRow.index > 0
          foreground: root.foreground
        }
        Item {
          width: parent.width
          implicitHeight: Math.max(intervalDetails.implicitHeight, inclusionControl.implicitHeight)
          height: implicitHeight
          Column {
            id: intervalDetails
            width: Math.max(0, parent.width - inclusionControl.width - Style.space(12))
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.spacing.labelGap
            Text {
              width: parent.width
              text: (intervalRow.modelData.kind === "epoch" ? "Epoch" : "Off-time") + " · "
                + Qt.formatDateTime(new Date(intervalRow.modelData.end.utcMs),
                  new Date(intervalRow.modelData.end.utcMs).getFullYear() === new Date().getFullYear()
                    ? "ddd, MMM d" : "MMM d, yyyy")
                + (intervalRow.modelData.recent ? " · Recent" : "")
              textFormat: Text.PlainText
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
              font.weight: Font.Medium
              wrapMode: Text.WordWrap
            }
            Text {
              width: parent.width
              readonly property bool sameDay: Qt.formatDateTime(new Date(intervalRow.modelData.start.utcMs), "yyyy-MM-dd")
                === Qt.formatDateTime(new Date(intervalRow.modelData.end.utcMs), "yyyy-MM-dd")
              text: Qt.formatDateTime(new Date(intervalRow.modelData.start.utcMs), sameDay ? "HH:mm" : "MMM d HH:mm") + " → "
                + Qt.formatDateTime(new Date(intervalRow.modelData.end.utcMs), sameDay ? "HH:mm" : "MMM d HH:mm") + " · "
                + (intervalRow.modelData.durationMs < 0 ? "Clock changed" : root.compactLength(intervalRow.modelData.durationMs))
              textFormat: Text.PlainText
              wrapMode: Text.WordWrap
              color: root.foreground
              opacity: 0.6
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
              MouseArea {
                id: stampHover
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
              }
              PanelToolTip {
                visible: root.tooltipsEnabled && stampHover.containsMouse
                text: Qt.formatDateTime(new Date(intervalRow.modelData.start.utcMs), "ddd, MMM d, yyyy · HH:mm:ss")
                  + " → " + Qt.formatDateTime(new Date(intervalRow.modelData.end.utcMs), "ddd, MMM d, yyyy · HH:mm:ss")
                fontFamily: root.fontFamily
              }
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
              objectName: "plancks_historyToggle_" + intervalRow.index
              anchors.horizontalCenter: parent.horizontalCenter
              trackHeight: Style.space(16)
              cursorPad: Style.space(4)
              checked: intervalRow.modelData.durationMs >= 0 && !intervalRow.modelData.excludedFromLearning
              enabled: EpochController.ready && !EpochController.busy && !EpochController.historyLoading
                && intervalRow.modelData.durationMs >= 0
              foreground: root.foreground
              activeFocusOnTab: true
              hasCursor: activeFocus
              Accessible.role: Accessible.CheckBox
              Accessible.name: intervalRow.modelData.kind === "epoch" ? "Use epoch for predictions" : "Use off-time for predictions"
              Accessible.description: intervalRow.sampleStatus
              Accessible.checkable: true
              Accessible.checked: checked
              onActiveFocusChanged: if (activeFocus) root.revealRequested(intervalRow)
              Keys.onSpacePressed: if (enabled) toggled()
              Keys.onReturnPressed: if (enabled) toggled()
              Keys.onEnterPressed: if (enabled) toggled()
              onToggled: {
                if (!enabled) return
                forceActiveFocus()
                root.focusSampleId = intervalRow.modelData.eventId
                EpochController.setHistoryInclusion(intervalRow.modelData.eventId, checked)
              }
              PanelToolTip {
                visible: root.tooltipsEnabled && inclusion.containsMouse
                text: "Use for predictions · " + intervalRow.sampleStatus
                fontFamily: root.fontFamily
              }
            }
            Text {
              id: inclusionLabel
              anchors.horizontalCenter: parent.horizontalCenter
              text: inclusion.checked ? "Included" : "Excluded"
              textFormat: Text.PlainText
              color: root.foreground
              opacity: inclusion.checked ? 0.75 : 0.55
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
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
      objectName: "plancks_historyPreviousButton"
      text: "Previous"
      foreground: root.foreground
      fontFamily: root.fontFamily
      fontSize: Style.font.bodySmall
      horizontalPadding: Style.space(8)
      bordered: enabled
      focusable: enabled
      opacity: enabled ? 1 : 0.35
      enabled: !EpochController.historyLoading && root.history.page > 0
      onActiveFocusChanged: if (activeFocus) root.revealRequested(previousButton)
      onClicked: if (enabled) root.changePage(root.history.page - 1)
    }
    Text {
      id: pageLabel
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
      objectName: "plancks_historyNextButton"
      text: "Next"
      foreground: root.foreground
      fontFamily: root.fontFamily
      fontSize: Style.font.bodySmall
      horizontalPadding: Style.space(8)
      bordered: enabled
      focusable: enabled
      opacity: enabled ? 1 : 0.35
      enabled: !EpochController.historyLoading && root.history.page + 1 < root.history.pages
      onActiveFocusChanged: if (activeFocus) root.revealRequested(nextButton)
      onClicked: if (enabled) root.changePage(root.history.page + 1)
      KeyNavigation.tab: root.backControl
    }
  }
  Text {
    width: parent.width
    visible: text !== ""
    text: [EpochController.historyError, EpochController.error].filter(function(x) { return !!x }).join("\n")
    textFormat: Text.PlainText
    wrapMode: Text.WordWrap
    color: root.foreground
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
  }
  Button {
    id: retryButton
    text: "Retry"
    visible: EpochController.historyError !== "" || EpochController.error !== ""
    enabled: !EpochController.busy && !EpochController.historyLoading
    focusable: true
    bordered: true
    foreground: root.foreground
    fontFamily: root.fontFamily
    fontSize: Style.font.bodySmall
    onActiveFocusChanged: if (activeFocus) root.revealRequested(retryButton)
    onClicked: {
      if (!enabled) return
      if (EpochController.error) EpochController.retry()
      EpochController.requestHistory(EpochController.historyPage)
    }
  }
}
