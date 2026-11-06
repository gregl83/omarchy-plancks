#!/usr/bin/env python3
"""Render notification snapshots from the production QML graphics, offscreen."""
import argparse
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
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--graphic", choices=("sun-moon", "coffee", "starship", "roadster"))
args = parser.parse_args()
frames = []
for graphic in ([args.graphic] if args.graphic else ("sun-moon", "coffee", "starship", "roadster")):
    for phase in ("active", "off-time"):
        levels = set(range(0, 101, 5))
        if graphic == "roadster" and phase == "active":
            levels.update(range(45, 56))
        for level in sorted(levels):
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
  width: 464; height: 432
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
      }, Qt.size(464, 432))
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
# Keep the Roadster's position and scale stable throughout flight. Independent
# trims would enlarge the inverted car when its bottom plume is suppressed.
flight = [frame for frame in frames if frame["graphic"] == "roadster"
          and frame["phase"] == "active" and not frame["learning"] and not frame["overtime"]]
flight_crop = None
if flight:
    bounds = []
    for frame in flight:
        geometry = subprocess.check_output(
            [magick, frame["path"], "-trim", "-format", "%w %h %X %Y", "info:"], text=True)
        w, h, x, y = map(int, geometry.split())
        bounds.append((x, y, x + w, y + h))
    left = min(b[0] for b in bounds)
    top = min(b[1] for b in bounds)
    right = max(b[2] for b in bounds)
    bottom = max(b[3] for b in bounds)
    flight_crop = f"{right-left}x{bottom-top}+{left}+{top}"
for frame in frames:
    crop = ["-crop", flight_crop] if frame in flight else ["-trim"]
    subprocess.run([magick, frame["path"], *crop, "+repage",
                    "-resize", "108x108", "-gravity", "center",
                    "-background", "none", "-extent", "116x116",
                    "PNG32:" + frame["path"]], check=True)
print(f"Rendered {len(frames)} notification images in assets/notifications")
