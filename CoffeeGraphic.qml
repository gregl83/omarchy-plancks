import QtQuick

Item {
  id: root
  property color foreground: "white"
  property real fill: 0
  property bool learning: false
  property bool animated: false
  property string phase: "off"
  property bool overtime: false
  property real motion: 0
  onFillChanged: cupDrawing.requestPaint()
  onLearningChanged: cupDrawing.requestPaint()
  onMotionChanged: cupDrawing.requestPaint()
  onForegroundChanged: cupDrawing.requestPaint()
  Timer {
    interval: 100
    repeat: true
    running: root.animated && root.learning
    onTriggered: root.motion = (root.motion + 0.035) % 1
  }
    Canvas {
      id: cupDrawing
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
        function bowl() {
          ctx.beginPath()
          ctx.moveTo(7, 16)
          ctx.lineTo(35, 16)
          ctx.lineTo(32, 36)
          ctx.quadraticCurveTo(31, 41, 21, 41)
          ctx.quadraticCurveTo(11, 41, 10, 36)
          ctx.closePath()
        }
        // Clip the liquid to the cup's curved interior.
        if (root.fill > 0) {
          ctx.save()
          bowl()
          ctx.clip()
          var surface = 40 - root.fill * 22
          ctx.globalAlpha = 0.3
          ctx.fillRect(7, surface, 28, 26)
          ctx.globalAlpha = 0.7
          ctx.beginPath()
          ctx.moveTo(7, surface)
          ctx.quadraticCurveTo(14, surface - 1.5, 21, surface)
          ctx.quadraticCurveTo(28, surface + 1.5, 35, surface)
          ctx.stroke()
          ctx.restore()
        }
        bowl()
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(35, 20)
        ctx.bezierCurveTo(49, 18, 48, 34, 33, 34)
        ctx.stroke()
        ctx.globalAlpha = 0.45
        ctx.beginPath()
        ctx.moveTo(5, 44)
        ctx.quadraticCurveTo(21, 48, 38, 44)
        ctx.stroke()
        if (root.learning) {
          ctx.globalAlpha = 0.25
          for (var i = 0; i < 2; ++i) {
            var drift = Math.sin((root.motion + i * 0.4) * Math.PI * 2) * 2
            var x = 16 + i * 10
            ctx.beginPath()
            ctx.moveTo(x, 11)
            ctx.bezierCurveTo(x - 3 + drift, 8, x + 3 + drift, 6, x, 3)
            ctx.stroke()
          }
        }
      }
    }
}
