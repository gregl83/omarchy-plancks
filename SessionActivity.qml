import QtQuick
import qs.Commons
import qs.Ui

Column {
  id: root
  property var activity: ({})
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  property bool tooltipsEnabled: true
  readonly property real cellSize: Style.space(8)
  readonly property real cellGap: Style.space(2)
  readonly property real pitch: cellSize + cellGap
  readonly property real gridHeight: 7 * pitch - cellGap
  readonly property real groupGap: Style.space(4)
  readonly property var columns: fitColumns()
  readonly property int weeks: columns.length
  readonly property real gridWidth: columns.length ? columns[columns.length - 1] + cellSize : 0
  readonly property var cells: buildCells()
  readonly property real totalMs: cells.reduce(function(total, cell) { return total + (cell.future ? 0 : cell.durationMs) }, 0)
  spacing: Style.space(4)
  Accessible.name: "Daily activity, last " + weeks + " weeks"
  Accessible.description: "Included session activity by local finish date. Stronger shading means more activity."

  function dateKey(date) { return Qt.formatDateTime(date, "yyyy-MM-dd") }
  function fitColumns() {
    var count = Math.max(1, Math.min(26, Math.floor((width + cellGap) / pitch)))
    for (; count > 0; count--) {
      var naturalWidth = count * pitch - cellGap + Math.floor((count - 1) / 4) * groupGap
      if (naturalWidth > width && count > 1) continue
      var firstGroup = count % 4 || 4
      var extra = count > 1 ? Math.max(0, width - naturalWidth) / (count - 1) : 0
      var positions = []
      for (var week = 0; week < count; week++) {
        var group = week < firstGroup ? 0 : 1 + Math.floor((week - firstGroup) / 4)
        positions.push(week * (pitch + extra) + group * groupGap)
      }
      if (count > 1) positions[count - 1] = width - cellSize
      return positions
    }
    return [0]
  }
  function buildCells() {
    if (!activity.today) return []
    var parts = activity.today.split("-")
    var today = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]), 12)
    var start = new Date(today)
    start.setDate(start.getDate() - (today.getDay() + 6) % 7 - (weeks - 1) * 7)
    var result = []
    for (var i = 0; i < weeks * 7; i++) {
      var day = new Date(start)
      day.setDate(day.getDate() + i)
      var value = (activity.days || {})[dateKey(day)] || {durationMs: 0, sessions: 0}
      result.push({date: day, durationMs: value.durationMs, sessions: value.sessions, future: day > today})
    }
    return result
  }
  function shade(level) {
    return Qt.rgba(foreground.r, foreground.g, foreground.b, [0.05, 0.2, 0.35, 0.5][level])
  }
  function level(ms) { return ms <= 0 ? 0 : ms < 1800000 ? 1 : ms < 5400000 ? 2 : 3 }
  function length(value) {
    var minutes = Math.floor(value / 60000)
    if (minutes === 0) return value > 0 ? "<1m" : "0m"
    var hours = Math.floor(minutes / 60)
    var rest = minutes % 60
    return hours ? hours + "h" + (rest ? " " + rest + "m" : "") : rest + "m"
  }
  function help(cell) {
    var minutes = Math.floor(cell.durationMs / 60000)
    var duration = minutes >= 60 ? Math.floor(minutes / 60) + "h " + minutes % 60 + "m"
      : minutes ? minutes + "m" : cell.durationMs > 0 ? "<1m" : "0m"
    return Qt.formatDateTime(cell.date, "ddd, MMM d, yyyy") + " · " + duration + " activity · "
      + cell.sessions + (cell.sessions === 1 ? " session" : " sessions")
      + "\nIncluded sessions, grouped by finish date."
  }
  Item {
    width: parent.width
    height: Math.max(label.implicitHeight, total.implicitHeight)
    PanelSectionHeader {
      id: label
      width: Math.max(0, parent.width - total.width - Style.space(8))
      text: "DAILY ACTIVITY"
      foreground: root.foreground
      fontFamily: root.fontFamily
      elide: Text.ElideRight
    }
    Text {
      id: total
      objectName: "plancks_dailyActivityTotal"
      anchors.right: parent.right
      anchors.baseline: label.baseline
      text: root.length(root.totalMs)
      textFormat: Text.PlainText
      color: root.foreground
      opacity: 0.6
      font.family: root.fontFamily
      font.pixelSize: Style.font.caption
      Accessible.name: "Total activity in displayed weeks: " + text
    }
    MouseArea {
      id: titleHover
      anchors.fill: parent
      hoverEnabled: true
      acceptedButtons: Qt.NoButton
    }
    PanelToolTip {
      visible: root.tooltipsEnabled && titleHover.containsMouse
      text: root.length(root.totalMs) + " total included activity across the displayed weeks.\nLast " + root.weeks + " weeks · one square per day, four weeks per group (oldest group may be partial). Activity is grouped by session finish date."
      fontFamily: root.fontFamily
    }
  }
  Item {
    width: parent.width
    height: root.gridHeight
    Repeater {
      model: root.cells
      delegate: Rectangle {
        id: cell
        required property var modelData
        required property int index
        x: root.columns[Math.floor(index / 7)]
        y: (index % 7) * root.pitch
        width: root.cellSize
        height: root.cellSize
        radius: Style.space(1)
        visible: !modelData.future
        color: root.shade(root.level(modelData.durationMs))
        Accessible.name: root.help(modelData)
        MouseArea {
          id: hover
          anchors.fill: parent
          hoverEnabled: true
          acceptedButtons: Qt.NoButton
        }
        PanelToolTip {
          visible: root.tooltipsEnabled && hover.containsMouse
          text: root.help(cell.modelData)
          fontFamily: root.fontFamily
        }
      }
    }
  }
}
