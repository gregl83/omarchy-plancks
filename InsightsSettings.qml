import QtQuick
import qs.Commons
import qs.Ui
import "."

Column {
  id: root
  property var hostWidget: null
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  property Item previousControl: null
  property Item nextControl: null
  property string thresholdError: ""
  readonly property bool insightsEnabled: hostWidget && hostWidget.insightsEnabled
  readonly property bool finishEnabled: hostWidget && hostWidget.finishNotificationsEnabled
  readonly property real previewButtonHeight: preview.height
  property alias firstControl: occasional
  readonly property Item lastControl: thresholds.enabled ? thresholds : finish
  signal backRequested()
  signal revealRequested(var item)
  spacing: Style.space(10)

  function setPreference(key, value) {
    if (hostWidget) hostWidget.setInsightPreference(key, value)
  }
  function thresholdsText() {
    return (hostWidget ? hostWidget.finishWarningSeconds : [1800, 60]).map(function(v) { return String(v / 60) }).join(", ")
  }
  function saveThresholds() {
    var parts = thresholds.text.split(",")
    if (parts.length < 1 || parts.length > 6 || parts.some(function(part) {
      return !/^\s*\d+(?:\.\d+)?\s*$/.test(part) || Number(part) < 1 / 60 || Number(part) > 1440
    })) {
      thresholdError = "Enter 1–6 minute values from 0.02 to 1440, separated by commas."
      return
    }
    var values = parts.map(function(part) { return Math.round(Number(part) * 60) })
    values = values.filter(function(v, i) { return values.indexOf(v) === i }).sort(function(a, b) { return b - a })
    thresholdError = ""
    setPreference("finishWarningSeconds", values)
    thresholds.text = thresholdsText()
  }
  Connections {
    target: root.hostWidget
    function onSettingsChanged() {
      if (!thresholds.activeFocus) thresholds.text = root.thresholdsText()
    }
  }

  PanelSectionHeader {
    text: "INSIGHTS"
    foreground: root.foreground
    fontFamily: root.fontFamily
  }
  Item {
    width: parent.width
    height: Math.max(occasionalLabel.implicitHeight, occasional.implicitHeight)
    Text {
      id: occasionalLabel
      width: parent.width - occasional.width - Style.space(12)
      anchors.verticalCenter: parent.verticalCenter
      text: "Occasional insights"
      color: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    ToggleSwitch {
      id: occasional
      objectName: "plancks_insightsToggle"
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      trackHeight: Style.space(16)
      cursorPad: Style.space(4)
      checked: root.insightsEnabled
      foreground: root.foreground
      activeFocusOnTab: true
      hasCursor: activeFocus
      Accessible.role: Accessible.CheckBox
      Accessible.name: "Occasional insights"
      Accessible.checkable: true
      Accessible.checked: checked
      KeyNavigation.backtab: root.previousControl
      KeyNavigation.tab: cadence.enabled ? cadence : preview
      onToggled: { forceActiveFocus(); root.setPreference("insightsEnabled", !checked) }
      onActiveFocusChanged: if (activeFocus) root.revealRequested(occasional)
      Keys.onSpacePressed: toggled()
      Keys.onReturnPressed: toggled()
      Keys.onEnterPressed: toggled()
      Keys.onEscapePressed: root.backRequested()
    }
  }
  Text {
    width: parent.width
    text: "Positive notes, historical patterns, and an extra-time celebration. Active epochs only."
    wrapMode: Text.WordWrap
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
  Row {
    width: parent.width
    height: Math.max(cadence.implicitHeight, preview.implicitHeight)
    spacing: Style.space(16)
    ButtonGroup {
      id: cadence
      anchors.verticalCenter: parent.verticalCenter
      objectName: "plancks_insightFrequency"
      options: [{value: "light", label: "Light"}, {value: "standard", label: "Standard"}, {value: "frequent", label: "Frequent"}]
      value: root.hostWidget ? root.hostWidget.insightFrequency : "standard"
      enabled: root.insightsEnabled
      opacity: enabled ? 1 : 0.45
      foreground: root.foreground
      fontFamily: root.fontFamily
      fontSize: Style.font.caption
      KeyNavigation.backtab: occasional
      KeyNavigation.tab: preview
      onChanged: function(value) { root.setPreference("insightFrequency", value) }
      onActiveFocusChanged: if (activeFocus) root.revealRequested(cadence)
      Keys.onEscapePressed: root.backRequested()
    }
    Rectangle {
      width: Math.max(1, Style.normalBorderWidth)
      height: Math.max(Style.space(12), cadence.height - Style.space(8))
      anchors.verticalCenter: parent.verticalCenter
      color: root.foreground
      opacity: 0.2
    }
    Button {
      id: preview
      objectName: "plancks_previewInsightButton"
      anchors.verticalCenter: parent.verticalCenter
      text: "Preview"
      Accessible.name: "Preview notification"
      tooltipText: root.hostWidget && root.hostWidget.tooltipsEnabled ? "Send a sample insight notification." : ""
      foreground: root.foreground
      fontFamily: root.fontFamily
      fontSize: Style.font.caption
      focusable: true
      enabled: EpochController.ready && !EpochController.notification.running
      bordered: true
      height: cadence.height
      KeyNavigation.backtab: cadence.enabled ? cadence : occasional
      KeyNavigation.tab: finish
      onClicked: EpochController.requestInsightPreview()
      onActiveFocusChanged: if (activeFocus) root.revealRequested(preview)
      Keys.onEscapePressed: root.backRequested()
    }
  }
  Text {
    width: parent.width
    text: "First note around 90 minutes. Then " + (cadence.value === "light" ? "every 3–4 hours." : cadence.value === "frequent" ? "every 1–2 hours." : "every 2–3 hours.")
    wrapMode: Text.WordWrap
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
  Item {
    width: parent.width
    height: Math.max(finishLabel.implicitHeight, finish.implicitHeight)
    Text {
      id: finishLabel
      width: parent.width - finish.width - Style.space(12)
      anchors.verticalCenter: parent.verticalCenter
      text: "Finish notifications"
      color: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    ToggleSwitch {
      id: finish
      objectName: "plancks_finishNotificationsToggle"
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      trackHeight: Style.space(16)
      cursorPad: Style.space(4)
      checked: root.finishEnabled
      foreground: root.foreground
      activeFocusOnTab: true
      hasCursor: activeFocus
      Accessible.role: Accessible.CheckBox
      Accessible.name: "Finish notifications"
      Accessible.checkable: true
      Accessible.checked: checked
      KeyNavigation.backtab: preview
      KeyNavigation.tab: thresholds.enabled ? thresholds : root.nextControl
      onToggled: { forceActiveFocus(); root.setPreference("finishNotificationsEnabled", !checked) }
      onActiveFocusChanged: if (activeFocus) root.revealRequested(finish)
      Keys.onSpacePressed: toggled()
      Keys.onReturnPressed: toggled()
      Keys.onEnterPressed: toggled()
      Keys.onEscapePressed: root.backRequested()
    }
  }
  Text {
    width: parent.width
    text: "Notify this many minutes before the expected end."
    wrapMode: Text.WordWrap
    color: root.foreground
    opacity: 0.6
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
  TextField {
    id: thresholds
    objectName: "plancks_finishWarningMinutes"
    width: parent.width
    enabled: root.finishEnabled
    opacity: enabled ? 1 : 0.45
    placeholderText: "30, 1"
    Component.onCompleted: text = root.thresholdsText()
    maximumLength: 80
    foreground: root.foreground
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    Accessible.name: "Finish warning minutes, separated by commas"
    KeyNavigation.priority: KeyNavigation.BeforeItem
    KeyNavigation.backtab: finish
    KeyNavigation.tab: root.nextControl
    Keys.onReturnPressed: root.saveThresholds()
    Keys.onEnterPressed: root.saveThresholds()
    onEditingFinished: root.saveThresholds()
    onActiveFocusChanged: if (activeFocus) root.revealRequested(thresholds)
    Keys.onEscapePressed: { text = root.thresholdsText(); root.thresholdError = ""; root.backRequested() }
  }
  Text {
    width: parent.width
    visible: root.thresholdError !== ""
    text: root.thresholdError
    wrapMode: Text.WordWrap
    color: root.foreground
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
  Text {
    width: parent.width
    visible: EpochController.insightsError !== ""
    text: EpochController.insightsError
    wrapMode: Text.WordWrap
    color: root.foreground
    font.family: root.fontFamily
    font.pixelSize: Style.font.caption
  }
}
