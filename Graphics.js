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
