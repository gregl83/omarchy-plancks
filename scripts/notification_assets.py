#!/usr/bin/env python3
"""Render notification snapshots from the production QML graphics, offscreen."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
# Notification cards fit images into a square icon slot. Remove the animation
# canvas margins, then fit each static silhouette without changing its aspect.
magick = shutil.which("magick")
if not magick:
    raise SystemExit("Install ImageMagick to render tightly fitted notification assets.")
frames = []
for graphic in ("sun-moon", "coffee", "starship", "roadster"):
    for phase in ("active", "off-time"):
        for level in range(0, 101, 5):
            frames.append(dict(graphic=graphic, phase=phase, fill=level / 100,
                               learning=False, overtime=False, path=f"{graphic}/{phase}/fill-{level:03}.png"))
        for special in ("learning", "overtime"):
            frames.append(dict(graphic=graphic, phase=phase,
                               fill=1 if special == "overtime" and phase == "off-time" else 0,
                               learning=special == "learning", overtime=special == "overtime",
                               path=f"{graphic}/{special}/{phase}.png"))

with tempfile.TemporaryDirectory(prefix="plancks-notification-assets-") as directory:
    root = Path(directory)
    for name in ("AnimatedGraphic.qml", "CoffeeGraphic.qml", "StarshipGraphic.qml", "SunMoonGraphic.qml", "RoadsterGraphic.qml", "Graphics.js"):
        shutil.copy2(REPO / name, root / name)
    for frame in frames:
        path = REPO / "assets/notifications" / frame["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        frame["path"] = str(path)
    qml = r'''import QtQuick
import QtQuick.Window
Window {
  id: root
  width: 116; height: 108
  visible: true
  color: "transparent"
  property var frames: FRAMES
  property int index: 0
  readonly property var frame: frames[index]
  AnimatedGraphic {
    id: drawing
    anchors.fill: parent
    graphic: root.frame.graphic
    foreground: "white"
    phase: root.frame.phase === "active" ? "active" : "off"
    fill: root.frame.fill
    learning: root.frame.learning
    overtime: root.frame.overtime
    animated: false
  }
  Timer {
    id: capture
    interval: 120
    running: true
    onTriggered: {
      drawing.grabToImage(function(result) {
        if (!result.saveToFile(root.frame.path)) {
          console.error("NOTIFICATION_ASSETS_FAIL " + root.frame.path)
          Qt.quit()
          return
        }
        if (root.index + 1 === root.frames.length) {
          console.log("NOTIFICATION_ASSETS_PASS")
          Qt.quit()
        } else {
          root.index++
          capture.restart()
        }
      }, Qt.size(116, 108))
    }
  }
}'''.replace("FRAMES", json.dumps(frames))
    (root / "shell.qml").write_text(qml)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               QT_SCALE_FACTOR="1", QT_SCREEN_SCALE_FACTORS="")
    result = subprocess.run(["quickshell", "-p", str(root), "--no-color"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    if result.returncode or "NOTIFICATION_ASSETS_PASS" not in result.stdout:
        raise SystemExit(result.stdout)
for frame in frames:
    subprocess.run([magick, frame["path"], "-trim", "+repage",
                    "-resize", "108x108", "-gravity", "center",
                    "-background", "none", "-extent", "116x116",
                    "PNG32:" + frame["path"]], check=True)
print(f"Rendered {len(frames)} notification images in assets/notifications")
