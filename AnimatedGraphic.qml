import QtQuick
import "Graphics.js" as Graphics

Loader {
  id: root
  // Wait for the caller's graphic binding before creating a drawing.
  property string graphic: ""
  property color foreground: "white"
  property real fill: 0
  property bool learning: false
  property bool animated: false
  property string phase: "off"
  property bool overtime: false
  source: graphic ? Qt.resolvedUrl(Graphics.option(graphic).source) : ""
  onLoaded: {
    item.foreground = Qt.binding(function() { return root.foreground })
    item.fill = Qt.binding(function() { return root.fill })
    item.learning = Qt.binding(function() { return root.learning })
    item.animated = Qt.binding(function() { return root.animated })
    item.phase = Qt.binding(function() { return root.phase })
    item.overtime = Qt.binding(function() { return root.overtime })
  }
}
