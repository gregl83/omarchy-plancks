import QtQuick
import "PreviewContext.js" as Desktop

Item {
  id: root
  // Panel crops use desktop coordinates at native logical size. The overview
  // scales that same desktop uniformly, cropping to fit its composition.
  property bool overview: false
  readonly property bool ready: wallpaper.status === Image.Ready
  readonly property real desktopScale: overview
    ? Math.max(width / Desktop.width, height / Desktop.height) : 1
  clip: true
  Item {
    width: Desktop.width
    height: Desktop.height
    scale: root.desktopScale
    transformOrigin: Item.TopLeft
    x: (root.width - width * scale) / 2
    y: root.overview ? (root.height - height * scale) / 2 : 0
    Image {
      id: wallpaper
      anchors.fill: parent
      source: Desktop.wallpaper
      // This is the same centered crop used by Omarchy's background renderer.
      fillMode: Image.PreserveAspectCrop
      smooth: true
    }
  }
}
