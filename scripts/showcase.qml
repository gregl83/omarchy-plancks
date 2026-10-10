import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import "Plancks" as Plancks
import "PreviewContext.js" as Desktop

ShellRoot {
  id: capture
  property string fontFamily: Style.font.family
  property color ink: Color.foreground
  property color muted: Color.muted
  property color accent: Color.accent
  property var hours: [7.5, 8.5, 7.75, 8.25, 8, 8]
  PanelWindow {
    id: window
    visible: true
    screen: Quickshell.screens.find(function(screen) { return screen.name === Desktop.screenName })
    implicitWidth: 1600
    implicitHeight: 1000
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    Item {
      id: stage
      width: 1600
      height: 1000
      PreviewWallpaper {
        id: wallpaper
        anchors.fill: parent
        overview: true
      }
      Rectangle { x: 76; y: 76; width: 4; height: 72; color: capture.accent }
      Text {
        x: 100; y: 67
        text: "Plancks"
        font.family: capture.fontFamily
        font.pixelSize: 68
        font.bold: true
        font.letterSpacing: -3
        color: capture.ink
      }
      Text {
        x: 100; y: 157
        text: "A second clock, tuned to your daily rhythm."
        font.family: capture.fontFamily
        font.pixelSize: 21
        color: capture.muted
      }
      Text {
        x: 1210; y: 100; width: 306
        horizontalAlignment: Text.AlignRight
        text: "OMARCHY / TIME"
        font.family: capture.fontFamily
        font.pixelSize: 17
        font.letterSpacing: 2
        color: capture.accent
      }
      Rectangle {
        x: 52; y: 276; width: 402; height: 452
        color: Color.popups.background
        radius: 8
      }
      Column {
        x: 76; y: 302; width: 354
        spacing: 25
        Text {
          text: "Your day.\nYour rhythm."
          color: capture.ink
          font.family: capture.fontFamily
          font.pixelSize: 43
          font.bold: true
          lineHeight: 1.2
        }
        Text {
          width: parent.width
          text: "Track your opportunity.\nLearn from your history.\nKeep your momentum."
          color: capture.muted
          font.family: capture.fontFamily
          font.pixelSize: 20
          lineHeight: 1.55
        }
        Rectangle { width: 48; height: 2; color: capture.accent }
        Text {
          text: "Built for your bar.\nLocal. Personal. Quiet."
          color: capture.muted
          font.family: capture.fontFamily
          font.pixelSize: 17
          lineHeight: 1.5
        }
      }
      // The main panel is a real frozen production capture, including bar context.
      Rectangle {
        x: 478; y: 233; width: 512; height: 654
        color: Color.popups.background
        border.color: Qt.rgba(capture.ink.r, capture.ink.g, capture.ink.b, 0.4)
        border.width: 1
        radius: 8
        Rectangle {
          x: 14; y: 14; width: parent.width; height: parent.height
          z: -1
          radius: 8
          color: Color.background
          opacity: 0.6
        }
        Image {
          id: mainPanel
          x: 2; y: 2; width: parent.width - 4; height: parent.height - 4
          source: "assets/preview-main.png"
          fillMode: Image.PreserveAspectFit
          smooth: true
        }
      }
      Column {
        x: 1044; y: 240; width: 480
        spacing: 24
        Rectangle {
          width: parent.width; height: 172
          color: Color.popups.background
          border.color: Qt.rgba(capture.ink.r, capture.ink.g, capture.ink.b, 0.2)
          radius: 8
          Column {
            x: 24; y: 22; width: parent.width - 48
            spacing: 16
            Text {
              text: "LEARN YOUR RHYTHM"
              font.family: capture.fontFamily
              font.pixelSize: 17
              font.letterSpacing: 1
              color: capture.accent
            }
            Plancks.HistoryTrend {
              title: "Epochs"
              foreground: capture.ink
              fontFamily: capture.fontFamily
              scale: 1.5
              transformOrigin: Item.TopLeft
              // Account for the scale so the genuine chart fits the showcase card.
              width: (parent.width / scale)
              tooltipsEnabled: false
              points: capture.hours.map(function(h, n) { return {durationMs: h * 3600000, excludedFromLearning: n === 5} })
            }
          }
        }
        Rectangle {
          width: parent.width; height: 220
          color: Color.popups.background
          border.color: Qt.rgba(capture.ink.r, capture.ink.g, capture.ink.b, 0.2)
          radius: 8
          Text {
            x: 24; y: 22
            text: "CHOOSE YOUR GRAPHIC"
            font.family: capture.fontFamily
            font.pixelSize: 17
            font.letterSpacing: 1
            color: capture.accent
          }
          Repeater {
            model: [{id: "coffee", name: "Coffee cup"}, {id: "starship", name: "Starship"}]
            Item {
              required property var modelData
              required property int index
              x: 24 + index * 218; y: 64; width: 214; height: 138
              Plancks.AnimatedGraphic {
                width: 94; height: 88
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.horizontalCenterOffset: modelData.id === "coffee" ? 6 : 0
                graphic: modelData.id
                foreground: capture.ink
                fill: 0.55
                phase: "active"
                animated: false
              }
              Text {
                y: 104; width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: modelData.name
                font.family: capture.fontFamily
                font.pixelSize: 18
                color: capture.ink
              }
            }
          }
        }
        Rectangle {
          width: parent.width; height: 173
          color: Color.popups.background
          border.color: Qt.rgba(capture.ink.r, capture.ink.g, capture.ink.b, 0.4)
          radius: 8
          Rectangle { x: 0; y: 20; width: 3; height: parent.height - 40; color: capture.accent }
          Text {
            x: 24; y: 24
            text: "PLANCKS  /  INSIGHTS"
            font.family: capture.fontFamily
            font.pixelSize: 16
            font.letterSpacing: 1
            color: capture.accent
          }
          Text {
            x: 24; y: 67; width: parent.width - 48
            text: "Extra time.\nSolid momentum."
            font.family: capture.fontFamily
            font.pixelSize: 24
            lineHeight: 1.25
            color: capture.ink
          }
        }
      }
      Rectangle { x: 76; y: 931; width: 1448; height: 1; color: Qt.rgba(capture.ink.r, capture.ink.g, capture.ink.b, 0.2) }
      Text {
        x: 76; y: 952
        text: "PREDICTIONS  /  HISTORY  /  INSIGHTS"
        font.family: capture.fontFamily
        font.pixelSize: 15
        font.letterSpacing: 1.5
        color: capture.muted
      }
      Text {
        x: 1124; y: 952; width: 400
        horizontalAlignment: Text.AlignRight
        text: "gregl83.plancks"
        font.family: capture.fontFamily
        font.pixelSize: 15
        color: capture.muted
      }
    }
  }
  Timer {
    interval: 700
    running: true
    repeat: true
    onTriggered: {
      if (!wallpaper.ready) return
      if (mainPanel.status !== Image.Ready) { console.error("SHOWCASE_FAIL main preview unavailable"); Qt.quit(); return }
      stage.grabToImage(function(result) {
        if (!result.saveToFile(SHOWCASE_PATH))
          console.error("SHOWCASE_FAIL saving image")
        else console.log("SHOWCASE_PASS")
        Qt.quit()
      }, Qt.size(Math.round(1600 / window.devicePixelRatio), Math.round(1000 / window.devicePixelRatio)))
    }
  }
}
