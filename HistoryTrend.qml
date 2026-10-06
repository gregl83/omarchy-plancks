import QtQuick
import qs.Commons
import qs.Ui

Column {
  id: root
  property string title: ""
  property var points: []
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  visible: points.length > 0
  spacing: Style.space(4)
  Accessible.name: title + " duration trend, " + points.length + " completed intervals"

  function length(value) {
    var minutes = Math.floor(value / 60000)
    if (minutes === 0) return value > 0 ? "<1m" : "0m"
    var hours = Math.floor(minutes / 60)
    var rest = minutes % 60
    return hours ? hours + "h" + (rest ? " " + rest + "m" : "") : rest + "m"
  }
  Item {
    width: parent.width
    height: Math.max(label.implicitHeight, latest.implicitHeight)
    PanelSectionHeader {
      id: label
      width: Math.max(0, parent.width - latest.width - Style.space(8))
      text: root.title.toUpperCase()
      foreground: root.foreground
      fontFamily: root.fontFamily
      elide: Text.ElideRight
    }
    Text {
      id: latest
      anchors.right: parent.right
      anchors.baseline: label.baseline
      text: root.points.length ? root.length(root.points[root.points.length - 1].durationMs) : ""
      textFormat: Text.PlainText
      color: root.foreground
      opacity: 0.6
      font.family: root.fontFamily
      font.pixelSize: Style.font.caption
    }
  }
  Canvas {
    id: plot
    width: parent.width
    height: Style.space(40)
    property var samples: root.points
    readonly property real inset: Style.space(4)
    onSamplesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections {
      target: root
      function onForegroundChanged() { plot.requestPaint() }
    }
    function pointX(index) {
      return samples.length > 1 ? inset + index * Math.max(0, width - inset * 2) / (samples.length - 1) : width / 2
    }
    onPaint: {
      var ctx = getContext("2d")
      ctx.clearRect(0, 0, width, height)
      if (!samples.length) return
      var minimum = samples[0].durationMs
      var maximum = minimum
      for (var sample of samples) {
        minimum = Math.min(minimum, sample.durationMs)
        maximum = Math.max(maximum, sample.durationMs)
      }
      var spread = maximum - minimum
      var positions = []
      for (var i = 0; i < samples.length; i++) {
        var y = spread > 0 ? inset + (maximum - samples[i].durationMs) / spread * (height - inset * 2) : height / 2
        positions.push({x: pointX(i), y: y})
      }
      ctx.lineWidth = Math.max(1, Style.normalBorderWidth)
      ctx.lineJoin = "round"
      ctx.strokeStyle = Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.55)
      ctx.beginPath()
      for (var j = 0; j < positions.length; j++) {
        if (j === 0) ctx.moveTo(positions[j].x, positions[j].y)
        else ctx.lineTo(positions[j].x, positions[j].y)
      }
      ctx.stroke()
      for (var k = 0; k < positions.length; k++) {
        var excluded = samples[k].excludedFromLearning
        ctx.beginPath()
        ctx.arc(positions[k].x, positions[k].y, Style.space(2), 0, Math.PI * 2)
        ctx.strokeStyle = Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, excluded ? 0.4 : 0.75)
        ctx.fillStyle = Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.75)
        if (!excluded) ctx.fill()
        ctx.stroke()
      }
    }
    MouseArea {
      id: hover
      anchors.fill: parent
      hoverEnabled: true
      acceptedButtons: Qt.NoButton
      readonly property int pointIndex: root.points.length < 2 ? 0
        : Math.max(0, Math.min(root.points.length - 1,
          Math.round((mouseX - plot.inset) / Math.max(1, plot.width - plot.inset * 2) * (root.points.length - 1))))
    }
    PanelToolTip {
      visible: hover.containsMouse && root.points.length > 0
      readonly property var sample: root.points.length ? root.points[hover.pointIndex] : null
      text: sample ? root.title + " · " + Qt.formatDateTime(new Date(sample.endUtcMs), "ddd, MMM d, yyyy")
        + " · " + root.length(sample.durationMs) + (sample.excludedFromLearning ? " · Excluded" : "") : ""
      fontFamily: root.fontFamily
    }
  }
}
