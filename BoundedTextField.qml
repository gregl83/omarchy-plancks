import QtQuick
import QtQuick.Controls as QQC
import Quickshell.Io
import qs.Commons
import qs.Ui

// TextArea checks clipboard formats without TextField's automatic payload read.
QQC.TextArea {
  id: root
  property color foreground: Color.foreground
  property color accent: Color.accent
  property int maximumLength: 256
  signal accepted()

  readonly property var borderSpec: Border.controlSpec(activeFocus ? "focus" : (hovered ? "hover-cursor" : "normal"), foreground, accent)
  textFormat: TextEdit.PlainText
  wrapMode: TextEdit.Wrap
  selectByMouse: true
  activeFocusOnTab: true
  font.family: Style.font.family
  font.pixelSize: Style.font.body
  color: foreground
  selectionColor: Style.selectionFillFor(foreground, accent)
  selectedTextColor: foreground
  placeholderTextColor: Qt.darker(foreground, 1.6)
  leftPadding: Style.spacing.controlPaddingX + Border.left(borderSpec)
  rightPadding: Style.spacing.controlPaddingX + Border.right(borderSpec)
  topPadding: Style.spacing.inputPaddingY + Border.top(borderSpec)
  bottomPadding: Style.spacing.inputPaddingY + Border.bottom(borderSpec)
  background: BorderSurface {
    color: Style.controlFill(root.activeFocus, root.hovered, root.foreground, root.accent)
    borderSpec: root.borderSpec
    radius: Style.cornerRadius
  }

  QQC.ContextMenu.menu: null
  Keys.priority: Keys.BeforeItem
  Keys.onPressed: function(event) {
    if (event.matches(StandardKey.Paste)) {
      root.boundedPaste(false)
      event.accepted = true
    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
      root.accepted()
      event.accepted = true
    }
  }

  Connections {
    target: root
    function onTextChanged() {
      if (root.length > root.maximumLength) root.remove(root.maximumLength, root.length)
    }
  }

  function boundedPaste(primary) {
    if (readOnly || !enabled || reader.running) return
    reader.previousText = text
    reader.start = selectionStart
    reader.end = selectionEnd
    reader.cursor = cursorPosition
    reader.command = ["python3", decodeURIComponent(Qt.resolvedUrl("clipboard_read.py").toString().replace(/^file:\/\//, "")),
                      String(maximumLength * 4), primary ? "primary" : "clipboard"]
    reader.running = true
  }

  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.MiddleButton
    cursorShape: Qt.IBeamCursor
    onPressed: function(mouse) {
      root.forceActiveFocus()
      root.cursorPosition = root.positionAt(mouse.x, mouse.y)
    }
    onClicked: root.boundedPaste(true)
  }

  Process {
    id: reader
    property string previousText
    property int start
    property int end
    property int cursor
    stdout: StdioCollector { id: output; waitForEnd: true }
    onExited: function(code, status) {
      if (code !== 0 || !root.activeFocus || root.readOnly || !root.enabled
          || root.text !== previousText || root.cursorPosition !== cursor
          || root.selectionStart !== start || root.selectionEnd !== end) return
      var value = JSON.parse(output.text).replace(/[\r\n\u2028\u2029]+/g, " ")
      value = value.slice(0, root.maximumLength - (root.length - (end - start)))
      if (!value) return
      root.remove(start, end)
      root.insert(start, value)
      root.cursorPosition = start + value.length
    }
  }
}
