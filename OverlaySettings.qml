import QtQuick
import qs.Commons
import qs.Ui

Column {
  id: root
  property var hostWidget: null
  property color foreground: "white"
  property string fontFamily: Style.font.family
  property Item previousControl: null
  property Item nextControl: null
  property alias firstControl: mode
  property alias lastControl: backing
  readonly property var config: hostWidget ? hostWidget.settings : ({})
  signal backRequested()
  signal revealRequested(var item)
  spacing: Style.space(10)
  function save(key, value) { if (hostWidget) hostWidget.setOverlayPreference(key, value) }
  Keys.onEscapePressed: backRequested()
  PanelSectionHeader { text: "OVERLAY CLOCK"; foreground: root.foreground; fontFamily: root.fontFamily }
  ButtonGroup {
    id: mode
    objectName: "plancks_overlayMode"
    options: [{value: "off", label: "Off"}, {value: "always", label: "Always"}, {value: "countdown", label: "Final countdown"}]
    value: root.config.overlayMode || "off"
    foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.caption
    onChanged: function(value) { root.save("overlayMode", value) }
    KeyNavigation.backtab: root.previousControl
    KeyNavigation.tab: seconds
    onActiveFocusChanged: if (activeFocus) root.revealRequested(mode)
  }
  Text {
    width: parent.width
    textFormat: Text.PlainText
    text: "A click-through clock on the focused screen. Follows the bar timer and stays visible through overrun."
    wrapMode: Text.WordWrap
    color: root.foreground; opacity: 0.6
    font.family: root.fontFamily; font.pixelSize: Style.font.caption
  }
  Text { textFormat: Text.PlainText; text: "Countdown lead time (seconds, 1–600)"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  BoundedTextField {
    id: seconds
    objectName: "plancks_overlaySeconds"
    width: parent.width
    maximumLength: 3
    text: String(root.config.overlaySeconds || 60)
    foreground: root.foreground
    font.family: root.fontFamily; font.pixelSize: Style.font.caption
    Accessible.name: "Overlay countdown seconds"
    onEditingFinished: {
      var value = Number(text)
      if (/^\d+$/.test(text) && value >= 1 && value <= 600) root.save("overlaySeconds", value)
      else text = String(root.config.overlaySeconds || 60)
    }
    KeyNavigation.backtab: mode
    KeyNavigation.tab: opacityChoice
    onActiveFocusChanged: if (activeFocus) root.revealRequested(seconds)
    Keys.onEscapePressed: root.backRequested()
  }
  Text { textFormat: Text.PlainText; text: "Opacity"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  ButtonGroup {
    id: opacityChoice
    options: [{value: "0.4", label: "40%"}, {value: "0.65", label: "65%"}, {value: "0.85", label: "85%"}]
    value: String(root.config.overlayOpacity || 0.65)
    foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.caption
    onChanged: function(value) { root.save("overlayOpacity", Number(value)) }
    KeyNavigation.backtab: seconds
    KeyNavigation.tab: backing
    onActiveFocusChanged: if (activeFocus) root.revealRequested(opacityChoice)
  }
  Text { textFormat: Text.PlainText; text: "Background"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  ButtonGroup {
    id: backing
    options: [{value: "none", label: "None"}, {value: "translucent", label: "Translucent"}]
    value: root.config.overlayBackground === true ? "translucent" : "none"
    foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.font.caption
    onChanged: function(value) { root.save("overlayBackground", value === "translucent") }
    KeyNavigation.backtab: opacityChoice
    KeyNavigation.tab: root.nextControl
    onActiveFocusChanged: if (activeFocus) root.revealRequested(backing)
  }
}
