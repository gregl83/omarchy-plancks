import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "."

Column {
  id: root
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  property bool tooltipsEnabled: true
  property var draft: defaults()
  property int revision: 0
  signal backRequested()
  signal revealRequested(var item)
  spacing: Style.space(10)
  function duration(minutes) {
    return minutes >= 60 ? Math.floor(minutes / 60) + "h"
      + (minutes % 60 ? " " + minutes % 60 + "m" : "") : minutes + "m"
  }
  function defaults() { return {name: "", preset: "pomodoro", presetVersion: 1, focusMinutes: 25, shortBreakMinutes: 5,
    longBreakMinutes: 15, longBreakEnabled: true, longBreakEvery: 4, rounds: 4, finalBreak: true} }
  function load(config) { draft = Object.assign(defaults(), config || {}); revision++ }
  function edit(key, value) { var next = Object.assign({}, draft); next[key] = value; next.preset = "custom"; draft = next }
  readonly property string validation: {
    for (var key of ["focusMinutes", "shortBreakMinutes", "longBreakMinutes", "longBreakEvery", "rounds"]) {
      var max = key === "rounds" || key === "longBreakEvery" ? 12 : 180
      if (!Number.isInteger(draft[key]) || draft[key] < 1 || draft[key] > max)
        return "Enter whole minutes from 1–180 and round counts from 1–12."
    }
    return ""
  }
  readonly property var summary: {
    if (validation) return {minutes: 0, breaks: 0, longBreaks: 0}
    var total = draft.rounds * draft.focusMinutes, count = 0, longs = 0
    for (var n = 1; n <= draft.rounds; n++) if (n < draft.rounds || draft.finalBreak) {
      var longBreak = draft.longBreakEnabled && n % draft.longBreakEvery === 0
      count++; if (longBreak) longs++
      total += longBreak ? draft.longBreakMinutes : draft.shortBreakMinutes
    }
    return {minutes: total, breaks: count, longBreaks: longs}
  }
  Keys.onEscapePressed: backRequested()
  PanelSectionHeader { text: "SESSION"; foreground: root.foreground; fontFamily: root.fontFamily }
  ButtonGroup {
    objectName: "plancks_sessionPreset"
    options: [{value: "pomodoro", label: "Pomodoro"}, {value: "custom", label: "Custom"}]
    fontFamily: root.fontFamily
    fontSize: Style.font.caption
    value: root.draft.preset
    foreground: root.foreground
    onChanged: function(value) { if (value === "pomodoro") root.load(null); else root.edit("preset", "custom") }
  }
  Column {
    width: parent.width
    visible: root.draft.preset === "custom"
    spacing: Style.space(6)
    Text {
      text: "Session name (optional)"
      color: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    BoundedTextField {
      id: sessionName
      objectName: "plancks_sessionName"
      width: parent.width
      maximumLength: 80
      placeholderText: "Reading, exercise, writing…"
      foreground: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
      Accessible.name: "Session name (optional)"
      Component.onCompleted: text = root.draft.name || ""
      Connections {
        target: root
        function onRevisionChanged() { sessionName.text = root.draft.name || "" }
        function onDraftChanged() { if (!sessionName.activeFocus) sessionName.text = root.draft.name || "" }
      }
      onTextChanged: if (text !== (root.draft.name || "")) root.edit("name", text)
      onActiveFocusChanged: if (activeFocus) root.revealRequested(sessionName)
      Keys.onEscapePressed: root.backRequested()
    }
  }
  component NumberSetting: Column {
    id: fieldRow
    required property string settingKey
    required property string label
    Layout.fillWidth: true
    Layout.preferredWidth: 1
    spacing: Style.space(6)
    Text {
      text: fieldRow.label
      color: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    BoundedTextField {
      id: number
      maximumLength: 3
      wrapMode: TextEdit.NoWrap
      objectName: "plancks_session_" + fieldRow.settingKey
      width: parent.width
      Component.onCompleted: text = String(root.draft[fieldRow.settingKey])
      Connections {
        target: root
        function onRevisionChanged() { number.text = String(root.draft[fieldRow.settingKey]) }
        function onDraftChanged() { if (!number.activeFocus) number.text = String(root.draft[fieldRow.settingKey]) }
      }
      foreground: root.foreground
      font.family: root.fontFamily
      font.pixelSize: Style.font.bodySmall
      Accessible.name: fieldRow.label
      onTextChanged: {
        if (!activeFocus) return
        var value = text.trim() === "" ? 0 : Number(text)
        if (value !== root.draft[fieldRow.settingKey]) root.edit(fieldRow.settingKey, value)
      }
      onActiveFocusChanged: if (activeFocus) root.revealRequested(fieldRow)
      Keys.onEscapePressed: root.backRequested()
    }
  }
  PanelSeparator { foreground: root.foreground }
  PanelSectionHeader { text: "TIMING"; foreground: root.foreground; fontFamily: root.fontFamily }
  GridLayout {
    width: parent.width
    columns: 3
    columnSpacing: Style.space(12)
    NumberSetting { settingKey: "focusMinutes"; label: "Activity (min)" }
    NumberSetting { settingKey: "shortBreakMinutes"; label: "Rest (min)" }
    NumberSetting { settingKey: "rounds"; label: "Rounds" }
  }
  PanelSeparator { foreground: root.foreground }
  PanelSectionHeader { text: "REST OPTIONS"; foreground: root.foreground; fontFamily: root.fontFamily }
  Repeater {
    model: [{key: "longBreakEnabled", label: "Long rests"}, {key: "finalBreak", label: "Include final rest"}]
    delegate: Item {
      id: optionRow
      required property var modelData
      width: root.width
      height: Math.max(optionLabel.implicitHeight, option.implicitHeight)
      Text { id: optionLabel; anchors.verticalCenter: parent.verticalCenter
        width: parent.width - option.width - Style.space(12); text: optionRow.modelData.label; color: root.foreground
        font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall }
      ToggleSwitch {
        id: option
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        trackHeight: Style.space(16)
        cursorPad: Style.space(4)
        objectName: "plancks_session_" + optionRow.modelData.key
        checked: root.draft[optionRow.modelData.key]
        foreground: root.foreground
        activeFocusOnTab: true
        hasCursor: activeFocus
        Accessible.role: Accessible.CheckBox
        Accessible.name: optionRow.modelData.label
        Accessible.checked: checked
        Accessible.checkable: true
        Accessible.description: optionRow.modelData.key === "finalBreak"
          ? "Add a rest after the final activity round."
          : "Replace regular rests with long rests at the configured cadence."
        PanelToolTip {
          visible: root.tooltipsEnabled && option.containsMouse
          text: option.Accessible.description
          fontFamily: root.fontFamily
        }
        onToggled: { forceActiveFocus(); root.edit(optionRow.modelData.key, !checked) }
        Keys.onSpacePressed: toggled()
        Keys.onReturnPressed: toggled()
        Keys.onEscapePressed: root.backRequested()
        onActiveFocusChanged: if (activeFocus) root.revealRequested(optionRow)
      }
    }
  }
  GridLayout {
    width: parent.width
    columns: 2
    columnSpacing: Style.space(12)
    NumberSetting { settingKey: "longBreakMinutes"; label: "Long rest (min)" }
    NumberSetting { settingKey: "longBreakEvery"; label: "Every N rounds" }
  }
  PanelSeparator { foreground: root.foreground }
  PanelSectionHeader { text: "SUMMARY"; foreground: root.foreground; fontFamily: root.fontFamily }
  Text {
    width: parent.width
    objectName: "plancks_sessionSummary"
    text: root.validation || root.draft.rounds + " × " + root.draft.focusMinutes + "m activity · " + root.summary.breaks
      + " rests · " + root.duration(root.summary.minutes) + " total"
      + (root.draft.longBreakEnabled && root.summary.longBreaks === 0 ? "\nNo long rest occurs in this sequence." : "")
    color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall; wrapMode: Text.WordWrap
  }
  Text {
    width: parent.width
    visible: EpochController.state.predictedEndUtcMs !== null
    text: {
      var timer = EpochController.state.timer
      var parts = timer.replace(/^[−+]/, "").split(":")
      var remaining = Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2])
      var minutes = Math.ceil((timer.indexOf("−") === 0 ? remaining : -remaining) / 60)
      var overlap = root.summary.minutes - minutes
      return "Epoch estimate: " + root.duration(Math.max(0, minutes)) + " remaining."
        + (overlap > 0 ? "\nThis session extends " + root.duration(overlap) + " beyond the current epoch estimate." : "")
    }
    color: root.foreground; opacity: 0.7; font.family: root.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.WordWrap
  }
  Text { width: parent.width; text: EpochController.error; visible: text.length > 0
    color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall; wrapMode: Text.WordWrap }
  Button {
    text: "Retry"
    visible: EpochController.error.length > 0
    enabled: !EpochController.busy
    focusable: true
    foreground: root.foreground
    fontSize: Style.font.bodySmall
    onClicked: EpochController.retry()
  }
  Button {
    objectName: "plancks_startSession"
    text: "Start session"
    Accessible.description: "Start the first activity stage; save these settings for next time."
    tooltipText: root.tooltipsEnabled ? Accessible.description : ""
    foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.bodySmall
    focusable: true
    bordered: true
    opacity: enabled ? 1 : 0.4
    enabled: !root.validation && EpochController.ready && !EpochController.busy && EpochController.state.phase === "active" && !EpochController.state.session
    onClicked: EpochController.sessionAction("session_started", Object.assign({}, root.draft, {name: (root.draft.name || "").trim()}))
    onActiveFocusChanged: if (activeFocus) root.revealRequested(this)
    Keys.onEscapePressed: root.backRequested()
  }
}
