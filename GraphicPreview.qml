import QtQuick
import "."
import "Graphics.js" as Graphics

AnimatedGraphic {
  id: root
  property bool running: false
  property int elapsed: 0
  readonly property var frame: Graphics.previewFrame(elapsed)
  readonly property string stateLabel: frame.state.label
  fill: frame.state.from + (frame.state.to - frame.state.from) * frame.progress
  learning: frame.state.learning
  phase: frame.state.phase
  overtime: frame.state.overtime === true
  animated: running
  opacity: frame.state.phase === "off" ? 0.45 : 1
}
