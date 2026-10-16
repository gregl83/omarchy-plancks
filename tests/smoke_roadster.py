#!/usr/bin/env python3
"""Check the Roadster's progress-driven halfway maneuver with offscreen production QML."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='plancks-roadster-check-') as directory:
    root = Path(directory)
    shutil.copy2(repo / 'RoadsterGraphic.qml', root)
    (root / 'shell.qml').write_text('''import QtQuick
import QtQuick.Window
import QtTest
Window {
  id: window
  property bool ready: false
  property bool done: false
  Timer { interval: 100; running: window.done; onTriggered: Qt.quit() }
  Timer { interval: 150; running: true; onTriggered: window.ready = true }
  visible: true
  width: 116; height: 108
  RoadsterGraphic { id: car; anchors.fill: parent }
  TestCase { name: "Lifetime"; when: false }
  TestCase {
    name: "RoadsterHalfway"
    when: window.ready
    function verify(condition, message) {
      if (!condition) { console.error("ROADSTER_FAIL " + message); window.done = true; throw new Error(message) }
    }
    function compare(actual, expected, message) {
      verify(actual === expected, (message || "Compare") + ": " + actual + " !== " + expected)
    }
    function angle(expected) {
      verify(Math.abs(car.rollAngle - expected) < 0.0001,
             "Expected " + expected + " degrees, got " + car.rollAngle)
    }
    function test_halfway() {
      car.phase = "active"
      car.animated = true
      var fills = [1, 0.55, 0.525, 0.5, 0.475, 0.45, 0.1, 0]
      var angles = [0, 0, 90, 180, 270, 360, 360, 360]
      for (var i = 0; i < fills.length; i++) {
        car.fill = fills[i]
        angle(angles[i])
        compare(car.turning, fills[i] < 0.55 && fills[i] > 0.45,
                "Side jets only between 45% and 55% elapsed")
      }
      car.fill = 1
      compare(car.altitude, 0, "Starts on the ground")
      car.fill = 0.775
      verify(Math.abs(car.altitude - 0.5) < 0.0001, "Half ascent at 22.5% elapsed")
      car.fill = 0.55
      compare(car.altitude, 1, "Peak height at the start of the roll")
      car.fill = 0.5
      compare(car.altitude, 1, "Peak height through the roll")
      car.fill = 0.45
      compare(car.altitude, 1, "Descent starts after the roll")
      car.fill = 0.225
      verify(Math.abs(car.altitude - 0.5) < 0.0001, "Half descent at 77.5% elapsed")
      car.fill = 0
      compare(car.altitude, 0, "Lands at the expected end")
      car.fill = 0.55
      verify(Math.abs(car.liftThrust - 1) < 0.0001, "Full lift before the roll")
      car.fill = 0.525
      verify(car.liftThrust < 0.0001, "Lift tapers out at the quarter turn")
      car.fill = 0.5
      verify(car.liftThrust < 0.0001 && car.turning, "Inverted car uses lateral thrust")
      car.fill = 0.46
      verify(car.liftThrust > 0.5, "Bottom thrust returns to catch the car")
      car.fill = 0.45
      verify(Math.abs(car.liftThrust - 1) < 0.0001 && !car.turning, "Full lift after the roll")
      car.fill = 0.44
      verify(car.catchBoost > 0.7, "Strong catch just after returning upright")
      car.fill = 0.35
      verify(car.catchBoost < 0.0001, "Catch settles after the roll")
      car.animated = false
      car.fill = 1
      compare(car.groundWash, 1, "Strong takeoff ground wash")
      car.fill = 0.5
      compare(car.groundWash, 0, "No ground cloud at altitude")
      car.fill = 0
      compare(car.groundWash, 1, "Strong touchdown ground wash")
      car.overtime = true
      compare(car.groundWash, 0, "Ground wash clears when parked after touchdown")
      car.overtime = false
      car.fill = 0.9
      verify(car.enginesOn && car.groundWash > 0, "Near-ground ascent has thrust and wash")
      car.fill = 0.1
      verify(car.enginesOn && car.groundWash > 0, "Near-ground descent has thrust and wash")
      car.fill = 0.5
      compare(car.groundWash, 0, "Mid-flight exhaust has no ground wash")
      car.animated = true
      car.overtime = true
      wait(100)
      verify(car.lift > 0 && car.enginesOn, "Engines continue throughout landing ease")
      wait(450)
      verify(car.lift > 0 && car.groundWash > 0, "Landing ease keeps ground wash near the surface")
      wait(250)
      compare(car.lift, 0, "Landing ease finishes on ground")
      verify(!car.enginesOn && car.groundWash === 0, "Exhaust stops only after resting")
      car.overtime = false
      car.fill = 0.5
      wait(200)
      angle(180) // Wall time cannot advance the roll.
      car.animated = false
      car.fill = 0.475
      angle(270) // Hidden panels and stills reflect progress immediately.
      car.animated = true
      angle(270)
      car.learning = true
      angle(0)
      verify(!car.turning)
      car.learning = false
      angle(270)
      car.overtime = true
      angle(0)
      verify(!car.turning)
      car.overtime = false
      car.phase = "off"
      angle(0)
      verify(!car.turning)
      car.phase = "active"
      angle(270) // Reopening midway restores the correct orientation.
      console.log("ROADSTER_HALFWAY_PASS")
      window.done = true
    }
  }
}''')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    if result.returncode or 'ROADSTER_HALFWAY_PASS' not in result.stdout or 'FAIL!' in result.stdout:
        raise SystemExit(result.stdout)
    print('Roadster halfway maneuver passed: 45–55% ratio, fixed-time independence, hidden/still rendering, learning, landing.')
