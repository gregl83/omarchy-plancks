.pragma library

function mode(settings) {
  var value = settings.overlayMode
  return ["off", "always", "countdown"].indexOf(value) >= 0 ? value : "off"
}
function lead(settings) {
  var value = settings.overlaySeconds
  return typeof value === "number" && isFinite(value) && value >= 1 && value <= 600
    ? Math.round(value) : 60
}
function opacity(settings) {
  var value = settings.overlayOpacity
  return typeof value === "number" && isFinite(value) && value >= 0.2 && value <= 1 ? value : 0.65
}
function view(state, settings) {
  var session = state.session
  var timer = String((session ? session.timer : state.timer) || "--:--:--")
  var match = /^([−+\-])(\d+):(\d{2}):(\d{2})$/.exec(timer)
  var seconds = match ? Number(match[2]) * 3600 + Number(match[3]) * 60 + Number(match[4]) : NaN
  var prediction = state.phase === "active" ? state.predictedEndUtcMs : state.predictedStartUtcMs
  var hasTarget = !!session || typeof prediction === "number" && isFinite(prediction)
  var due = hasTarget && match && (match[1] === "+" || seconds <= lead(settings))
  return {timer: timer, symbol: session ? (session.kind === "focus" ? "A" : "R") : (state.phase === "active" ? "E" : "O"),
    paused: !!session && session.status === "paused",
    show: mode(settings) === "always" || mode(settings) === "countdown" && !!due}
}
