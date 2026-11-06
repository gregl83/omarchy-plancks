import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Commons
import "OverlayLogic.js" as OverlayLogic

PanelWindow {
  id: root
  property var timerState: ({})
  property var config: ({})
  property bool operational: false
  readonly property var frame: OverlayLogic.view(timerState, config)
  readonly property real sizeScale: OverlayLogic.scale(config)
  readonly property bool showing: operational && frame.show
  screen: {
    var monitor = Hyprland.focusedMonitor
    var screens = Quickshell.screens
    for (var i = 0; i < screens.length; i++)
      if (monitor && screens[i].name === monitor.name) return screens[i]
    return screens.length ? screens[0] : null
  }
  visible: showing
  color: "transparent"
  anchors.bottom: true
  margins.bottom: Style.space(32) * sizeScale + Style.bar.sizeHorizontal
  implicitWidth: (clockRow.implicitWidth + Style.space(56)) * sizeScale
  implicitHeight: (clockRow.implicitHeight + Style.space(28)) * sizeScale
  exclusionMode: ExclusionMode.Ignore
  WlrLayershell.namespace: "plancks-clock-overlay"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
  // An empty surface input region passes pointer/touch input to the window below.
  mask: Region {}

  Item {
    anchors.centerIn: parent
    width: root.width / root.sizeScale
    height: root.height / root.sizeScale
    scale: root.sizeScale
    Canvas {
      anchors.fill: parent
      opacity: OverlayLogic.opacity(root.config)
      visible: OverlayLogic.background(root.config)
      onWidthChanged: requestPaint()
      onHeightChanged: requestPaint()
      onAvailableChanged: if (available) requestPaint()
      onVisibleChanged: if (visible) requestPaint()
      onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.clearRect(0, 0, width, height)
        var inset = 3, radius = Math.min(Style.space(7), height / 5)
        function pane(x, y, w, h, r) {
          ctx.beginPath()
          ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y)
          ctx.lineTo(x + w, y + r)
          ctx.lineTo(x + w, y + h - r)
          ctx.lineTo(x + w - r, y + h)
          ctx.lineTo(x + r, y + h)
          ctx.lineTo(x, y + h - r)
          ctx.lineTo(x, y + r); ctx.lineTo(x + r, y)
          ctx.closePath()
        }
        // Soft outer separation around a shallow, chamfered glass instrument frame.
        for (var depth = 3; depth > 0; depth--) {
          pane(inset - depth * 0.6, inset + depth * 0.3,
               width - inset * 2 + depth * 1.2, height - inset * 2, radius + depth)
          ctx.strokeStyle = "rgba(0, 0, 0, 0.08)"
          ctx.lineWidth = 1.5; ctx.stroke()
        }
        pane(inset, inset, width - inset * 2, height - inset * 2, radius)
        var smoke = ctx.createLinearGradient(0, 0, 0, height)
        smoke.addColorStop(0, "rgba(53, 61, 70, 0.34)")
        smoke.addColorStop(0.35, "rgba(23, 29, 36, 0.48)")
        smoke.addColorStop(0.70, "rgba(19, 25, 32, 0.50)")
        smoke.addColorStop(1, "rgba(46, 57, 67, 0.32)")
        ctx.fillStyle = smoke; ctx.fill()
        ctx.save(); ctx.clip()
        // Feathered reflections avoid the hard diagonal of a metal faceplate.
        var reflection = ctx.createRadialGradient(width * 0.18, -height * 0.6, 0,
                                                  width * 0.18, -height * 0.6, width * 0.75)
        reflection.addColorStop(0, "rgba(240, 248, 255, 0.12)")
        reflection.addColorStop(0.60, "rgba(221, 239, 255, 0.025)")
        reflection.addColorStop(1, "rgba(221, 239, 255, 0)")
        ctx.fillStyle = reflection; ctx.fillRect(0, 0, width, height)
        var glow = ctx.createRadialGradient(width * 0.86, height * 1.8, 0,
                                           width * 0.86, height * 1.8, height * 2)
        glow.addColorStop(0, "rgba(181, 214, 245, 0.10)")
        glow.addColorStop(1, "rgba(181, 214, 245, 0)")
        ctx.fillStyle = glow; ctx.fillRect(0, 0, width, height)
        ctx.restore()
        // Uneven rim lighting gives the edge thickness without a rigid frame.
        var edge = ctx.createLinearGradient(0, 0, width, height)
        edge.addColorStop(0, "rgba(249, 253, 255, 0.58)")
        edge.addColorStop(0.3, "rgba(229, 243, 255, 0.12)")
        edge.addColorStop(0.6, "rgba(221, 237, 255, 0.06)")
        edge.addColorStop(1, "rgba(235, 247, 255, 0.40)")
        pane(inset + 0.5, inset + 0.5, width - inset * 2 - 1, height - inset * 2 - 1, radius)
        ctx.strokeStyle = edge; ctx.lineWidth = 1; ctx.stroke()
        var inner = ctx.createLinearGradient(0, 0, 0, height)
        inner.addColorStop(0, "rgba(240, 250, 255, 0.07)")
        inner.addColorStop(0.4, "rgba(240, 250, 255, 0)")
        inner.addColorStop(1, "rgba(215, 236, 255, 0.05)")
        pane(inset + 2, inset + 2, width - inset * 2 - 4, height - inset * 2 - 4, radius - 1)
        ctx.strokeStyle = inner; ctx.stroke()

      }
    }
    opacity: root.showing ? 1 : 0
    Row {
      id: clockRow
      // Let the lettering fade with the glass, with a small contrast reserve.
      opacity: Math.min(1, OverlayLogic.opacity(root.config) + 0.15)
      anchors.centerIn: parent
      spacing: Style.space(10)
      Text {
        anchors.verticalCenter: parent.verticalCenter
        textFormat: Text.PlainText
        text: root.frame.paused ? "Ⅱ" : ""
        visible: root.frame.paused
        color: "#f2f6fa"
        font.family: Style.font.family
        font.pixelSize: Style.space(16)
        renderType: Text.QtRendering
        antialiasing: true
      }
      Text {
        anchors.verticalCenter: parent.verticalCenter
        textFormat: Text.RichText
        text: "<i>t</i><sub>" + root.frame.symbol + "</sub>"
        color: "#f2f6fa"
        font.family: Style.font.family
        font.pixelSize: Style.space(20)
        renderType: Text.QtRendering
        antialiasing: true
        style: Text.Raised
        styleColor: OverlayLogic.background(root.config) ? "#50070e16" : "#90070e16"
      }
      Text {
        textFormat: Text.PlainText
        text: root.frame.timer
        color: "#f2f6fa"
        font.family: Style.font.family
        font.pixelSize: Style.space(36)
        renderType: Text.QtRendering
        antialiasing: true
        font.weight: Font.DemiBold
        style: Text.Raised
        styleColor: OverlayLogic.background(root.config) ? "#50070e16" : "#90070e16"
      }
    }
    // No pulsing or animation on timer ticks. Respect the shell motion setting.
    NumberAnimation on opacity {
      from: 0; to: 1
      duration: typeof Style.duration === "function" ? Style.duration(180) : 180
      easing.type: Easing.OutCubic
      running: root.showing
    }
  }
}
