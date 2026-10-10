import QtQuick
import qs.Commons
import qs.Ui
import "."
import "Graphics.js" as Graphics

BarWidget {
  id: root
  moduleName: "gregl83.plancks"
  readonly property var epoch: EpochController.state
  readonly property bool tooltipsEnabled: setting("tooltipsEnabled", true) !== false
  function setTooltipsEnabled(enabled) {
    settings = Object.assign({}, settings, {tooltipsEnabled: enabled})
    if (bar && bar.shell) bar.shell.updateEntryInline(moduleName, settings)
    if (!enabled && bar) bar.hideTooltip(button)
  }
  readonly property string animatedGraphic: Graphics.option(setting("animatedGraphic", "coffee")).id
  function setAnimatedGraphic(id) {
    var selected = Graphics.option(id).id
    settings = Object.assign({}, settings, {animatedGraphic: selected})
    if (bar && bar.shell) bar.shell.updateEntryInline(moduleName, settings)
  }
  readonly property bool opened: panel.opened
  readonly property bool popoutSwitchClosing: panel.popoutSwitchClosing
  readonly property real openPanelIndicatorWidth: label.implicitWidth
  readonly property real openPanelIndicatorHeight: Style.space(10)
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function open() { panel.open() }
  function close() { panel.close() }
  function toggle() { panel.toggle() }
  function closeForPopoutSwitch() { panel.closeForPopoutSwitch() }
  onSettingsChanged: EpochController.configure(settings)
  Component.onCompleted: EpochController.configure(settings)

  WidgetButton {
    id: button
    objectName: "plancks_widgetButton"
    anchors.fill: parent
    bar: root.bar
    labelVisible: false
    hasVisualContent: true
    dimmed: root.epoch.phase !== "active" && EpochController.error === ""
    fixedWidth: root.vertical ? root.barSize : label.implicitWidth + Style.space(18)
    fixedHeight: root.vertical ? label.implicitHeight + Style.space(14) : root.barSize
    tooltipText: root.tooltipsEnabled ? EpochController.error || root.epoch.status : ""
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: "Plancks. " + root.epoch.status + ". " + root.epoch.timer
    Keys.onReturnPressed: root.toggle()
    Keys.onSpacePressed: root.toggle()
    onPressed: function(b) { if (b === Qt.LeftButton) root.toggle() }

    Rectangle {
      anchors.fill: parent
      color: "transparent"
      border.width: button.activeFocus ? 1 : 0
      border.color: button.foreground
      radius: Style.cornerRadius
    }
    Text {
      id: label
      // Rich text handles hover itself; keep the button's input surface above it.
      z: -1
      anchors.centerIn: parent
      textFormat: Text.RichText
      text: {
        var warning = EpochController.error ? "! " : ""
        var notation = "<i>t</i><sub>P</sub>"
        var timer = root.epoch.timer || "--:--:--"
        if (root.vertical) return warning + notation + "<br>" + timer.replace(/:/g, "<br>")
        var gap = '<span style="font-size: ' + (button.fontSize / 2) + 'px">&#8202;</span>'
        return warning + notation + gap + timer
      }
      color: button.foreground
      font.family: button.fontFamily
      font.pixelSize: button.fontSize
      horizontalAlignment: Text.AlignHCenter
    }
  }

  EpochPanel {
    id: panel
    bar: root.bar
    anchorItem: button
    hostWidget: root
  }
}
