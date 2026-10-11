.pragma library

var options = [
  {id: "coffee", name: "Coffee cup", source: "CoffeeGraphic.qml", previewOffsetX: 4},
  {id: "starship", name: "Starship", source: "StarshipGraphic.qml"}
]

function option(id) {
  for (var i = 0; i < options.length; i++) {
    if (options[i].id === id) return options[i]
  }
  return options[0]
}

function seconds(value) {
  var parts = String(value).replace(/^[+−-]/, "").split(":")
  if (parts.length !== 3 || parts.some(function(p) { return !/^\d+$/.test(p) })) return NaN
  return Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2])
}

// Shared by the live drawing and notification snapshots.
function stateFrame(state) {
  var elapsed = seconds(state.elapsed)
  var timer = seconds(state.timer)
  var predicted = (state.phase === "active" ? state.predictedEndUtcMs : state.predictedStartUtcMs) != null
    && isFinite(timer) && isFinite(elapsed)
  var remaining = /^[−-]/.test(String(state.timer)) ? timer : -timer
  var fraction = Math.max(0, Math.min(1, remaining / Math.max(1, elapsed + remaining)))
  return {predicted: predicted, learning: !predicted && isFinite(timer),
          overtime: predicted && remaining < 0,
          fill: predicted ? (state.phase === "active" ? fraction : 1 - fraction) : 0}
}

function notificationImage(graphic, state) {
  var frame = stateFrame(state)
  var phase = state.phase === "active" ? "active" : "off-time"
  var path = "assets/notifications/" + option(graphic).id + "/"
  if (frame.learning) return path + "learning/" + phase + ".png"
  if (frame.overtime) return path + "overtime/" + phase + ".png"
  var level = String(Math.round(frame.fill * 20) * 5)
  return path + phase + "/fill-" + ("000" + level).slice(-3) + ".png"
}

var previewStates = [
    {label: "Ready to start", duration: 1600, phase: "off", from: 0, to: 0, learning: false},
    {label: "Epoch · learning", duration: 2400, phase: "active", from: 0, to: 0, learning: true},
    {label: "Epoch · countdown", duration: 3600, phase: "active", from: 1, to: 0, learning: false},
    {label: "Epoch · past expected end", overtime: true, duration: 1600, phase: "active", from: 0, to: 0, learning: false},
    {label: "Off-time · learning", duration: 2400, phase: "off", from: 0, to: 0, learning: true},
    {label: "Off-time · countdown", duration: 3600, phase: "off", from: 0, to: 1, learning: false},
    {label: "Off-time · past expected start", overtime: true, duration: 1600, phase: "off", from: 1, to: 1, learning: false}
  ]

function previewFrame(elapsed) {
  var offset = elapsed
  for (var i = 0; i < previewStates.length; i++) {
    if (offset < previewStates[i].duration)
      return {state: previewStates[i], progress: offset / previewStates[i].duration}
    offset -= previewStates[i].duration
  }
  return {state: previewStates[0], progress: 0}
}
