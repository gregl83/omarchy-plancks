import QtQuick

Item {
  id: root
  objectName: "plancks_starshipDrawing"
  property color foreground: "white"
  property real fill: 0
  property bool learning: false
  property bool animated: false
  property string phase: "off"
  property bool overtime: false
  property real motion: 0
  readonly property bool flameVisible: phase === "active" && !overtime
  readonly property bool padVisible: phase !== "active"
  readonly property bool fuelConnectionVisible: padVisible
  onFillChanged: drawing.requestPaint()
  onLearningChanged: drawing.requestPaint()
  onPhaseChanged: drawing.requestPaint()
  onOvertimeChanged: drawing.requestPaint()
  onMotionChanged: drawing.requestPaint()
  onForegroundChanged: drawing.requestPaint()
  Timer {
    interval: 100
    repeat: true
    running: root.animated && (root.flameVisible || (root.fuelConnectionVisible && root.learning))
    onTriggered: root.motion = (root.motion + 0.065) % 1
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
      // Slightly broaden the silhouette around its fixed center.
      ctx.translate(29, 0)
      ctx.scale(1.12, 1)
      ctx.translate(-29, 0)
      ctx.strokeStyle = root.foreground.toString()
      ctx.fillStyle = root.foreground.toString()
      ctx.lineWidth = 1.2
      ctx.lineCap = "round"
      ctx.lineJoin = "round"
      function hull() {
        ctx.beginPath()
        ctx.moveTo(29, 3)
        ctx.bezierCurveTo(31, 5, 32.5, 9, 32.5, 13)
        ctx.lineTo(32.5, 42)
        ctx.lineTo(25.5, 42)
        ctx.lineTo(25.5, 13)
        ctx.bezierCurveTo(25.5, 9, 27, 5, 29, 3)
        ctx.closePath()
      }
      if (!root.learning && root.fill > 0) {
        ctx.save()
        hull()
        ctx.clip()
        var surface = 41.5 - root.fill * 33
        ctx.globalAlpha = 0.3
        ctx.fillRect(25.5, surface, 7, 35)
        ctx.globalAlpha = 0.7
        ctx.beginPath()
        ctx.moveTo(25.5, surface)
        ctx.lineTo(32.5, surface)
        ctx.stroke()
        ctx.restore()
      }
      // Slim cylindrical hull, swept forward flaps and broad, flat aft flaps.
      // Keep the silhouette separate from the single fuel-level metaphor.
      ctx.beginPath()
      ctx.moveTo(26.2, 8.5); ctx.lineTo(21.8, 12); ctx.lineTo(21.8, 14.5); ctx.lineTo(25.5, 14.5)
      ctx.moveTo(31.8, 8.5); ctx.lineTo(36.2, 12); ctx.lineTo(36.2, 14.5); ctx.lineTo(32.5, 14.5)
      ctx.moveTo(25.5, 30); ctx.lineTo(21, 37); ctx.lineTo(21, 42); ctx.lineTo(25.5, 42)
      ctx.moveTo(32.5, 30); ctx.lineTo(37, 37); ctx.lineTo(37, 42); ctx.lineTo(32.5, 42)
      ctx.stroke()
      hull()
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(27, 42); ctx.lineTo(27, 43.5)
      ctx.moveTo(31, 42); ctx.lineTo(31, 43.5)
      ctx.stroke()
      if (root.flameVisible) {
        var flicker = Math.sin(root.motion * Math.PI * 2)
        ctx.globalAlpha = 0.65
        ctx.beginPath()
        ctx.moveTo(26.5, 44)
        ctx.quadraticCurveTo(26.5 + flicker * 0.5, 47, 29, 51 + flicker)
        ctx.quadraticCurveTo(31.5 - flicker * 0.5, 47, 31.5, 44)
        ctx.stroke()
        ctx.globalAlpha = 0.3
        ctx.beginPath()
        ctx.moveTo(27, 44); ctx.lineTo(29, 48 + flicker); ctx.lineTo(31, 44)
        ctx.fill()
      } else if (root.padVisible) {
        ctx.globalAlpha = 0.45
        ctx.beginPath()
        ctx.moveTo(12, 48); ctx.lineTo(46, 48)
        ctx.moveTo(25, 45); ctx.lineTo(25, 48)
        ctx.moveTo(33, 45); ctx.lineTo(33, 48)
        ctx.stroke()
        if (root.fuelConnectionVisible) {
          ctx.globalAlpha = root.learning ? 0.35 + Math.sin(root.motion * Math.PI * 2) * 0.15 : 0.45
          ctx.beginPath()
          ctx.moveTo(33.5, 26); ctx.lineTo(41, 26); ctx.lineTo(41, 45)
          ctx.stroke()
        }
      }
    }
  }
}
