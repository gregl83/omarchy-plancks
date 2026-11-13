import QtQuick
import qs.Commons
import qs.Ui
import "."

Column {
  id: root
  property var sample: null
  property int sequence: 0
  property string generation: ""
  property color foreground: "white"
  property string fontFamily: Style.font.family
  property bool submitted: false
  signal canceled()
  signal saved()
  signal revealRequested(var item)
  spacing: Style.space(12)
  function stamp(value) {
    var date = new Date(value)
    var offset = -date.getTimezoneOffset()
    function pad(value) { return ("0" + Math.floor(value)).slice(-2) }
    return Qt.formatDateTime(date, "yyyy-MM-dd'T'HH:mm:ss") + (offset >= 0 ? "+" : "-")
      + pad(Math.abs(offset) / 60) + ":" + pad(Math.abs(offset) % 60)
  }
  function parse(text) {
    var match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([+-])(\d{2}):(\d{2})$/.exec(text)
    if (!match || Number(match[4]) > 14 || Number(match[5]) > 59 || Number(match[4]) === 14 && Number(match[5]) !== 0) return NaN
    var value = Date.parse(text)
    var offset = (Number(match[4]) * 60 + Number(match[5])) * (match[3] === "+" ? 1 : -1)
    return isFinite(value) && new Date(value + offset * 60000).toISOString().slice(0, 19) === match[1] + "T" + match[2] ? value : NaN
  }
  function open(row, field) {
    sample = JSON.parse(JSON.stringify(row))
    sequence = EpochController.history.sequence
    generation = EpochController.history.generation
    submitted = false
    start.text = stamp(row.start.utcMs)
    end.text = stamp(row.end.utcMs)
    Qt.callLater(function() { (field === "end" ? end : start).forceActiveFocus() })
  }
  function exactTime(text, edge) {
    if (sample && text === stamp(sample[edge].utcMs)) return sample[edge].utcMs
    if (sample && sample.originalTimes && text === stamp(sample.originalTimes[edge].utcMs)) return sample.originalTimes[edge].utcMs
    return parse(text)
  }
  readonly property real startMs: exactTime(start.text, "start")
  readonly property real endMs: exactTime(end.text, "end")
  readonly property string validation: !isFinite(startMs) || !isFinite(endMs) ? "Use YYYY-MM-DDTHH:MM:SS±HH:MM with a UTC offset."
    : endMs <= startMs ? "End must be after start." : ""
  readonly property bool changed: !!sample && (startMs !== sample.start.utcMs || endMs !== sample.end.utcMs)
  function save() {
    if (!saveButton.enabled) return
    submitted = true
    EpochController.editHistoryTimes(sample.eventId, startMs, endMs, generation, sequence)
  }
  Connections {
    target: EpochController
    function onHistoryTimesSaved() { if (root.submitted) { root.submitted = false; root.saved() } }

  }
  Keys.onEscapePressed: if (!EpochController.busy) root.canceled()
  PanelSectionHeader { text: "EDIT INTERVAL"; foreground: root.foreground; fontFamily: root.fontFamily }
  Text {
    width: parent.width; textFormat: Text.PlainText; wrapMode: Text.WordWrap
    text: "Times include the date, seconds, and UTC offset. Shared boundaries also update the adjacent interval and predictions. Sessions keep their recorded times; Include/Exclude stays as selected."
    color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption
  }
  Text { text: "Start"; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily }
  BoundedTextField {
    id: start; objectName: "plancks_editStart"
    width: parent.width; maximumLength: 25; foreground: root.foreground
    font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
    Accessible.name: "Interval start date, time, and UTC offset"
    enabled: !EpochController.busy
    onActiveFocusChanged: if (activeFocus) root.revealRequested(start)
    onAccepted: end.forceActiveFocus()
  }
  Text { text: "End"; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily }
  BoundedTextField {
    id: end; objectName: "plancks_editEnd"
    width: parent.width; maximumLength: 25; foreground: root.foreground
    font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
    Accessible.name: "Interval end date, time, and UTC offset"
    enabled: !EpochController.busy
    onActiveFocusChanged: if (activeFocus) root.revealRequested(end)
    onAccepted: root.save()
  }
  Text {
    width: parent.width; textFormat: Text.PlainText; wrapMode: Text.WordWrap
    text: root.validation || ("Duration: " + Math.floor((root.endMs - root.startMs) / 3600000) + "h "
      + Math.floor((root.endMs - root.startMs) / 60000) % 60 + "m " + Math.floor((root.endMs - root.startMs) / 1000) % 60 + "s")
    color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
  }
  Text {
    width: parent.width; textFormat: Text.PlainText; wrapMode: Text.WordWrap
    visible: text !== ""; text: EpochController.error
    color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption
  }
  Row {
    spacing: Style.space(8)
    Button {
      id: saveButton; objectName: "plancks_saveTimes"; text: EpochController.busy ? "Saving…" : "Save changes"
      enabled: root.changed && !root.validation && EpochController.ready && !EpochController.busy
      foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.bodySmall; bordered: true; focusable: enabled
      onClicked: root.save()
    }
    Button {
      text: "Cancel"; objectName: "plancks_cancelTimes"; enabled: !EpochController.busy
      foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.bodySmall; focusable: enabled
      onClicked: root.canceled()
    }
  }
  Button {
    text: "Restore original times"; objectName: "plancks_restoreTimes"
    visible: !!root.sample && !!root.sample.edited
    enabled: !EpochController.busy
    foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.caption; focusable: true
    onClicked: {
      start.text = root.stamp(root.sample.originalTimes.start.utcMs)
      end.text = root.stamp(root.sample.originalTimes.end.utcMs)
      start.forceActiveFocus()
    }
  }
}
