import QtQuick

Item {
  id: root
  objectName: "plancks_roadsterDrawing"
  property color foreground: "white"
  property real fill: 0
  property bool learning: false
  property bool animated: false
  property string phase: "off"
  property bool overtime: false
  property real motion: 0
  readonly property bool airborne: phase === "active" && !overtime
  readonly property bool recharging: phase !== "active" && !overtime
  // Fill is the remaining epoch fraction. Rotate once across 45–55%
  // elapsed, so reopening or rendering a still preserves the correct angle.
  readonly property real rollProgress: !airborne || learning || fill >= 0.55 ? 0
    : fill <= 0.45 ? 1 : (0.55 - fill) / 0.10
  readonly property bool turning: airborne && !learning && fill < 0.55 && fill > 0.45
  readonly property real rollAngle: 360 * rollProgress
  // Lift jets taper away as the underside turns upward; side jets carry
  // the roll, then lift thrust returns smoothly to catch the upright car.
  readonly property real liftThrust: Math.pow(Math.max(0, Math.cos(rollAngle * Math.PI / 180)), 2)
  // Rise over the first 45%, hold the peak through the roll, and descend
  // over the last 45%. Smoothstep eases takeoff and touchdown.
  readonly property real altitudeRatio: !airborne ? 0 : learning ? 0.75
    : Math.max(0, Math.min(1, (1 - fill) / 0.45, fill / 0.45))
  readonly property real altitude: altitudeRatio * altitudeRatio * (3 - 2 * altitudeRatio)
  // A stronger catch continues briefly after the roll; ground wash is
  // strongest at takeoff/touchdown and fades with altitude.
  readonly property real catchBoost: !airborne || learning ? 0
    : Math.sin(Math.PI * Math.max(0, Math.min(1, ((1 - fill) - 0.525) / 0.125)))
  // Follow the displayed height during the landing ease, not its target.
  // Keep engines running until the visible car has actually settled.
  readonly property bool enginesOn: airborne || lift > 0
  readonly property real groundWash: !enginesOn ? 0 : Math.max(0, 1 - lift / 0.45)
  property real lift: altitude
  Behavior on lift { enabled: root.animated; NumberAnimation { duration: 700; easing.type: Easing.InOutQuad } }
  onFillChanged: drawing.requestPaint()
  onLearningChanged: drawing.requestPaint()
  onPhaseChanged: { motion = 0; drawing.requestPaint() }
  onOvertimeChanged: { motion = 0; drawing.requestPaint() }
  onRollProgressChanged: drawing.requestPaint()
  onLiftChanged: drawing.requestPaint()
  onMotionChanged: drawing.requestPaint()
  onForegroundChanged: drawing.requestPaint()
  Timer {
    interval: 100
    repeat: true
    running: root.animated && (root.enginesOn || root.recharging && root.learning)
    onTriggered: root.motion = (root.motion + 1 / 120) % 1
  }
  Canvas {
    id: drawing
    anchors.fill: parent
    onAvailableChanged: if (available) requestPaint()
    onPaint: {
      var ctx = getContext("2d")
      ctx.reset()
      ctx.clearRect(0, 0, width, height)
      ctx.scale(width / 58, height / 54)
      ctx.strokeStyle = root.foreground.toString()
      ctx.fillStyle = root.foreground.toString()
      ctx.lineWidth = 1.2
      ctx.lineCap = "round"
      ctx.lineJoin = "round"
      var cycle = root.motion * Math.PI * 2
      // Ground fades away during takeoff and returns only near touchdown.
      var ground = Math.max(0, 1 - root.lift * 2)
      if (ground > 0) {
        ctx.globalAlpha = 0.25 * ground
        ctx.beginPath(); ctx.moveTo(9, 47); ctx.lineTo(49, 47); ctx.stroke()
      }
      if (root.recharging) {
        ctx.globalAlpha = (root.learning ? 0.35 + 0.15 * Math.cos(cycle) : 0.4) * ground
        ctx.beginPath()
        ctx.moveTo(29, 47); ctx.lineTo(29, 44)
        ctx.moveTo(27, 44); ctx.lineTo(31, 44)
        ctx.stroke()
      }
      ctx.save()
      var bob = root.airborne ? Math.sin(cycle * 2) * 0.4 * root.lift : 0
      var angle = root.rollAngle * Math.PI / 180
      var thrust = root.liftThrust
      var catchPower = 1 + 0.7 * root.catchBoost
      // Engine output does not fade with altitude. Only the roll throttles
      // the lift plume; near the surface the ground intercepts the full jet.
      var exhaustPower = root.enginesOn ? 1 : 0
      var exhaustExtent = (0.15 + 0.85 * thrust) * exhaustPower
      var jetLength = exhaustPower * (3 + thrust * (19 + 5 * root.catchBoost + Math.sin(cycle * 6) * 1.2))
      if (root.groundWash > 0)
        jetLength = (47 - (35 - root.lift * 20 + bob)) / 0.75 - 10
      var jetSpread = (1 + 5 * thrust) * Math.max(0.2, exhaustPower) * (1 + 0.2 * root.catchBoost)
      if (root.groundWash > 0) jetSpread = Math.min(6, 1 + jetLength * 0.24)
      var clouds = []
      // Blend free exhaust into the impact cloud instead of removing all
      // vapor until the last trace of ground wash has disappeared.
      var vaporExtent = Math.min(exhaustExtent, jetLength / 24)
      var freeVapor = 1 - root.groundWash
      if (root.enginesOn && thrust > 0.02 && freeVapor > 0) {
        for (var cloudSide = -1; cloudSide <= 1; cloudSide += 2) {
          clouds.push({x: cloudSide * 12, y: 10 + 8 * vaporExtent, rx: 6 * exhaustExtent, ry: 5 * vaporExtent, alpha: 0.4 * thrust * catchPower * freeVapor})
          clouds.push({x: cloudSide * 12, y: 10 + 14 * vaporExtent, rx: 11 * exhaustExtent, ry: 7 * vaporExtent, alpha: 0.5 * thrust * catchPower * freeVapor})
          clouds.push({x: cloudSide * 12, y: 10 + 18 * vaporExtent, rx: 15 * exhaustExtent, ry: 6 * vaporExtent, alpha: 0.55 * thrust * catchPower * freeVapor})
        }
      }
      if (root.groundWash > 0) {
        // The same jet endpoint defines impact and outwash: no detached glow.
        // Small overlapping billows widen outward from each impact point.
        for (var impactSide = -1; impactSide <= 1; impactSide += 2) {
          var impactY = 10 + jetLength
          clouds.push({x: impactSide * 12, y: impactY - 1, rx: 4, ry: 3, alpha: 0.65 * root.groundWash})
          clouds.push({x: impactSide * 17, y: impactY + 0.7, rx: 6, ry: 3.5, alpha: 0.5 * root.groundWash})
          clouds.push({x: impactSide * 23, y: impactY + 1.5, rx: 6, ry: 2.8, alpha: 0.35 * root.groundWash})
        }
      }
      // Offset pulses keep the two exhaust streams from breathing in unison.
      // Vary the soft volumes before measuring their visible bounds.
      for (var vaporIndex = 0; vaporIndex < clouds.length; vaporIndex++) {
        var puff = clouds[vaporIndex]
        var pulse = Math.sin(cycle * 7 + vaporIndex * 1.7)
        var ripple = Math.sin(cycle * 11 + vaporIndex * 2.3)
        puff.rx *= 0.94 + 0.06 * pulse
        puff.ry *= 0.94 + 0.06 * ripple
        puff.alpha *= 0.9 + 0.1 * pulse
      }
      // Center the actual rotating silhouette at its source, including gas.
      // The corner samples bound the small body; plume tips dominate in flight.
      var bounds = [[-22,-1],[22,-1],[-15,-6],[15,-6],[-8,-9],[8,-9],
                    [-21,14],[21,14],[-13,11],[13,11],[0,-9]]
      if (root.lift > 0) {
        var wingTop = -2 - root.lift * 5
        bounds.push([-23.5, wingTop], [23.5, wingTop],
                    [-24.5, wingTop + 5.5], [24.5, wingTop + 5.5])
      }
      if (root.enginesOn) {
        for (var side = -1; side <= 1; side += 2) {
          if (root.turning) {
            bounds.push([side * 21, side * 3])
            bounds.push([side * 33, side * 3 - 3], [side * 33, side * 3 + 3])
          }
          bounds.push([side * 12 - jetSpread, 10 + jetLength], [side * 12 + jetSpread, 10 + jetLength])
        }
      }
      for (var c = 0; c < clouds.length; c++) {
        for (var sample = 0; sample < 64; sample++) {
          var theta = sample * Math.PI / 32
          bounds.push([clouds[c].x + clouds[c].rx * Math.cos(theta),
                       clouds[c].y + clouds[c].ry * Math.sin(theta)])
        }
      }
      var left = Infinity, right = -Infinity, top = Infinity, bottom = -Infinity
      for (var k = 0; k < bounds.length; k++) {
        var bx = bounds[k][0] * Math.cos(angle) - bounds[k][1] * Math.sin(angle)
        var by = bounds[k][0] * Math.sin(angle) + bounds[k][1] * Math.cos(angle)
        left = Math.min(left, bx); right = Math.max(right, bx)
        top = Math.min(top, by); bottom = Math.max(bottom, by)
      }
      var center = root.airborne ? (left + right) / 2 : 0
      // Peak height is close to Starship's upper extent. The visible bounds
      // provide only the clearance needed for the side jets during rotation.
      var bodyY = 35 - root.lift * 20 + bob
      if (root.airborne) bodyY = Math.max(1 - top * 0.75, Math.min(51 - bottom * 0.75, bodyY))
      ctx.translate(29 - center * 0.75, bodyY)
      ctx.scale(0.75, 0.75)
      ctx.rotate(angle)
      function body() {
        ctx.beginPath()
        ctx.moveTo(-22, -1)
        ctx.bezierCurveTo(-22, -4, -18, -4, -15, -6)
        ctx.bezierCurveTo(-12, -8.5, -9, -9, 0, -9)
        ctx.bezierCurveTo(9, -9, 12, -8.5, 15, -6)
        ctx.bezierCurveTo(18, -4, 22, -4, 22, -1)
        ctx.lineTo(21, 6)
        ctx.quadraticCurveTo(20, 9, 16, 9)
        ctx.lineTo(14, 9); ctx.lineTo(13, 11)
        ctx.lineTo(-13, 11); ctx.lineTo(-14, 9)
        ctx.lineTo(-16, 9)
        ctx.quadraticCurveTo(-20, 9, -21, 6)
        ctx.closePath()
      }
      // Tires are quiet, rounded masses rather than extra outlined boxes.
      ctx.globalAlpha = 0.55
      for (var side = -1; side <= 1; side += 2) {
        ctx.save(); ctx.scale(side, 1)
        ctx.beginPath()
        ctx.moveTo(15.5, 7); ctx.lineTo(21, 5); ctx.lineTo(21, 12.5)
        ctx.quadraticCurveTo(21, 14, 19.5, 14)
        ctx.lineTo(17, 14); ctx.quadraticCurveTo(15.5, 14, 15.5, 12.5)
        ctx.closePath(); ctx.fill(); ctx.restore()
      }
      if (!root.learning && root.fill > 0) {
        ctx.save(); body(); ctx.clip()
        var surface = 11 - 20 * root.fill
        ctx.globalAlpha = 0.25
        ctx.fillRect(-22, surface, 44, 20)
        ctx.restore()
      }
      ctx.globalAlpha = 1
      body(); ctx.stroke()
      // A single glass tone suggests the canopy without doubling its outline.
      ctx.globalAlpha = 0.12
      ctx.beginPath()
      ctx.moveTo(-12, -5)
      ctx.bezierCurveTo(-8, -8, 8, -8, 12, -5)
      ctx.quadraticCurveTo(0, -4, -12, -5)
      ctx.fill()
      // The wide light bar and deployed wing are the two crisp accents.
      ctx.globalAlpha = 0.9
      ctx.beginPath(); ctx.moveTo(-19, -1); ctx.lineTo(19, -1); ctx.stroke()
      if (root.lift > 0) {
        var wingY = -2 - root.lift * 5
        // Occlude the body behind the wing, with a small transparent gutter.
        // This stays legible on any panel background without a painted halo.
        ctx.save()
        ctx.globalCompositeOperation = "destination-out"
        ctx.globalAlpha = Math.min(1, root.lift * 4)
        ctx.lineWidth = 2.8
        ctx.beginPath()
        ctx.moveTo(-23.5, wingY)
        ctx.quadraticCurveTo(0, wingY - 1, 23.5, wingY)
        ctx.lineTo(24.5, wingY + 5.5)
        ctx.lineTo(22, wingY + 3.5)
        ctx.quadraticCurveTo(0, wingY + 1.2, -22, wingY + 3.5)
        ctx.lineTo(-24.5, wingY + 5.5)
        ctx.closePath()
        ctx.fill(); ctx.stroke()
        ctx.restore()
        // A deep pitched blade and swept endplates give the active wing
        // its broad, assertive face without adding fine aero-detail lines.
        ctx.beginPath()
        ctx.moveTo(-23.5, wingY)
        ctx.quadraticCurveTo(0, wingY - 1, 23.5, wingY)
        ctx.lineTo(22, wingY + 3.5)
        ctx.quadraticCurveTo(0, wingY + 1.2, -22, wingY + 3.5)
        ctx.closePath()
        ctx.globalAlpha = 0.6 * root.lift; ctx.fill()
        ctx.globalAlpha = 0.9 * root.lift; ctx.stroke()
        for (var tip = -1; tip <= 1; tip += 2) {
          ctx.beginPath()
          ctx.moveTo(tip * 23.5, wingY)
          ctx.lineTo(tip * 24.5, wingY + 5.5)
          ctx.lineTo(tip * 22, wingY + 3.5)
          ctx.closePath()
          ctx.globalAlpha = 0.5 * root.lift; ctx.fill()
          ctx.globalAlpha = 0.85 * root.lift; ctx.stroke()
        }
        // Short inboard struts connect the blade to the rear deck.
        ctx.globalAlpha = 0.65 * root.lift
        ctx.beginPath()
        ctx.moveTo(-10, wingY + 2); ctx.lineTo(-11, -1.8)
        ctx.moveTo(10, wingY + 2); ctx.lineTo(11, -1.8)
        ctx.stroke()
      }
      // Four small outlets retain the distinctive rear hardware; omit trim,
      // license plate, diffuser fins and panel seams at this icon size.
      ctx.globalAlpha = 0.65
      ctx.lineWidth = 1
      for (var n = 0; n < 4; n++) {
        ctx.beginPath(); ctx.arc(-9 + n * 6, 6, 1.1, 0, Math.PI * 2); ctx.stroke()
      }
      if (root.enginesOn) {
        // Overlapping soft volumes capture the broad vapor visible in the
        // reveal, rather than reducing the boosters to narrow cones.
        for (var c = 0; c < clouds.length; c++) {
          var cloud = clouds[c]
          ctx.save()
          ctx.translate(cloud.x, cloud.y)
          ctx.scale(cloud.rx, cloud.ry)
          var vapor = ctx.createRadialGradient(0, 0, 0, 0, 0, 1)
          vapor.addColorStop(0, root.foreground.toString())
          vapor.addColorStop(0.45, root.foreground.toString())
          vapor.addColorStop(1, "transparent")
          ctx.fillStyle = vapor
          ctx.globalAlpha = cloud.alpha * (0.9 + 0.1 * Math.sin(cycle * 4 + c % 3))
          ctx.beginPath(); ctx.arc(0, 0, 1, 0, Math.PI * 2); ctx.fill()
          ctx.restore()
        }
        function plume(x, y, rotation, length, spread, opacity) {
          if (length < 0.1 || exhaustPower <= 0) return
          // Fast overlapping pulses add irregularity without breaking the
          // nozzle connection or lifting the ground-impact endpoint.
          var pulse = Math.sin(cycle * 8 + x * 0.19)
          var ripple = Math.sin(cycle * 13 + x * 0.31)
          var impact = root.groundWash > 0 && rotation === 0
          if (!impact) length *= 0.94 + 0.04 * pulse + 0.02 * ripple
          spread *= 0.91 + 0.06 * ripple + 0.03 * pulse
          opacity *= 0.9 + 0.07 * pulse + 0.03 * ripple
          ctx.save()
          ctx.translate(x, y); ctx.rotate(rotation)
          var gas = ctx.createLinearGradient(0, 0, 0, length)
          gas.addColorStop(0, root.foreground.toString())
          gas.addColorStop(impact ? 0.85 : 0.3, root.foreground.toString())
          gas.addColorStop(1, impact
            ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.5).toString()
            : "transparent")
          ctx.fillStyle = gas
          ctx.globalAlpha = Math.min(1, opacity * exhaustPower * catchPower)
          ctx.beginPath()
          ctx.moveTo(-1.1, 0)
          ctx.quadraticCurveTo(-spread * (0.7 + 0.1 * ripple), length * 0.4, -spread, length)
          ctx.lineTo(spread, length)
          ctx.quadraticCurveTo(spread * (0.7 - 0.1 * ripple), length * 0.4, 1.1, 0)
          ctx.closePath(); ctx.fill()
          ctx.restore()
        }
        // Broad lift plumes and opposed side jets make the maneuver readable.
        for (var j = -1; j <= 1; j += 2) {
          plume(j * 12, 10, 0, jetLength, jetSpread, 0.12 + 0.73 * thrust)
          plume(j * 12, 10, 0, jetLength * (root.groundWash > 0 ? 1 : 0.8), 0.6 + 1.8 * thrust, 0.1 + 0.55 * thrust)
          if (root.turning)
            plume(j * 21, j * 3, -j * Math.PI / 2, 12, 3, 0.45 + 0.4 * Math.sin(root.rollProgress * Math.PI))
        }
      }
      ctx.restore()
    }
  }
}
