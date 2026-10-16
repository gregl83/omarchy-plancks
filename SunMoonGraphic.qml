import QtQuick

Item {
  id: root
  objectName: "plancks_sunMoonDrawing"
  property color foreground: "white"
  property real fill: 0
  property bool learning: false
  property bool animated: false
  property string phase: "off"
  property bool overtime: false
  property real motion: 0
  readonly property bool ready: phase !== "active" && !learning && !overtime && fill === 0
  property real daylight: phase === "active" || ready ? 1 : 0
  property real elevation: ready || overtime ? 0 : learning ? 1 : phase === "active" ? fill : 1 - fill
  Behavior on daylight { enabled: root.animated; NumberAnimation { duration: 650 } }
  Behavior on elevation { enabled: root.animated; NumberAnimation { duration: 650 } }
  onDaylightChanged: drawing.requestPaint()
  onElevationChanged: drawing.requestPaint()
  onLearningChanged: drawing.requestPaint()
  onOvertimeChanged: drawing.requestPaint()
  onMotionChanged: drawing.requestPaint()
  onForegroundChanged: drawing.requestPaint()
  Timer {
    interval: 100
    repeat: true
    running: root.animated && !root.ready
    onTriggered: root.motion = (root.motion + 0.0125) % 1
  }
  Canvas {
    id: drawing
    anchors.fill: parent
    onAvailableChanged: if (available) requestPaint()
    onPaint: {
      var ctx = getContext("2d")
      ctx.reset()
      ctx.clearRect(0, 0, width, height)
      ctx.scale(width / 58, height / 54)
      ctx.strokeStyle = root.foreground.toString()
      ctx.fillStyle = root.foreground.toString()
      ctx.lineWidth = 1.5
      ctx.lineCap = "round"
      ctx.lineJoin = "round"
      var cycle = root.motion * Math.PI * 2
      var pulse = root.overtime ? 0.65 + 0.25 * Math.cos(cycle) : 1
      var y = 47 - root.elevation * 31
      // The fixed horizon defines symmetric bounds in every frame.
      ctx.globalAlpha = 0.28
      ctx.lineWidth = 1.2
      ctx.beginPath()
      ctx.moveTo(9, 49); ctx.quadraticCurveTo(29, 47, 49, 49)
      ctx.stroke()
      ctx.lineWidth = 1.5
      ctx.save()
      ctx.beginPath()
      ctx.moveTo(7, 0); ctx.lineTo(51, 0); ctx.lineTo(51, 48)
      ctx.quadraticCurveTo(29, 46, 7, 48)
      ctx.closePath(); ctx.clip()
      if (root.daylight > 0) {
        ctx.save()
        ctx.translate(29, y)
        ctx.globalAlpha = root.daylight * pulse
        ctx.beginPath(); ctx.arc(0, 0, 7, 0, Math.PI * 2); ctx.stroke()
        ctx.globalAlpha *= 0.18
        ctx.fill()
        ctx.globalAlpha = root.daylight * pulse * 0.75
        ctx.rotate(cycle)
        for (var i = 0; i < 8; i++) {
          ctx.rotate(Math.PI / 4)
          ctx.beginPath(); ctx.moveTo(10, 0); ctx.lineTo(13, 0); ctx.stroke()
        }
        ctx.restore()
      }
      if (root.daylight < 1) {
        ctx.save()
        ctx.translate(30.875, y)
        ctx.globalAlpha = (1 - root.daylight) * pulse
        ctx.beginPath()
        ctx.moveTo(3, -8)
        ctx.bezierCurveTo(-10, -8, -10, 8, 3, 8)
        ctx.bezierCurveTo(-4, 4, -4, -4, 3, -8)
        ctx.closePath(); ctx.stroke()
        ctx.globalAlpha *= 0.18; ctx.fill()
        ctx.restore()
        var stars = [{x: 13, y: 16, radius: 1.5},
                     {x: 39, y: 5, radius: 1},
                     {x: 46, y: 26, radius: 1.8}]
        for (var s = 0; s < stars.length; s++) {
          var star = stars[s]
          var x = star.x
          var sy = star.y
          var r = star.radius
          ctx.globalAlpha = (1 - root.daylight) * root.elevation * (0.4 + 0.2 * Math.cos(cycle + s * 2.1))
          ctx.beginPath()
          ctx.moveTo(x - r, sy); ctx.lineTo(x + r, sy)
          ctx.moveTo(x, sy - r); ctx.lineTo(x, sy + r)
          ctx.stroke()
        }
      }
      ctx.restore()
    }
  }
}
