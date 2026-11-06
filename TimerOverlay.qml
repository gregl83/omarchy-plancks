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
  margins.bottom: Style.space(32) + Style.bar.sizeHorizontal
  implicitWidth: clockRow.implicitWidth + Style.space(40)
  implicitHeight: clockRow.implicitHeight + Style.space(24)
  exclusionMode: ExclusionMode.Ignore
  WlrLayershell.namespace: "plancks-clock-overlay"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
  // An empty surface input region passes pointer/touch input to the window below.
  mask: Region {}

  Rectangle {
    anchors.fill: parent
    radius: Style.space(12)
    color: root.config.overlayBackground === true ? Qt.rgba(0, 0, 0, 0.55) : "transparent"
    opacity: root.showing ? 1 : 0
    Row {
      id: clockRow
      anchors.centerIn: parent
      spacing: Style.space(10)
      opacity: OverlayLogic.opacity(root.config)
      Text {
        anchors.verticalCenter: parent.verticalCenter
        textFormat: Text.PlainText
        text: root.frame.paused ? "Ⅱ" : ""
        visible: root.frame.paused
        color: "white"
        font.pixelSize: Style.space(16)
      }
      Text {
        anchors.verticalCenter: parent.verticalCenter
        textFormat: Text.RichText
        text: "<i>t</i><sub>" + root.frame.symbol + "</sub>"
        color: "white"
        font.pixelSize: Style.space(20)
        style: Text.Outline
        styleColor: "#60000000"
      }
      Text {
        textFormat: Text.PlainText
        text: root.frame.timer
        color: "white"
        font.family: "monospace"
        font.pixelSize: Style.space(36)
        font.weight: Font.Light
        style: Text.Outline
        styleColor: "#60000000"
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
