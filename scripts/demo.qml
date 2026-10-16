import QtQuick
import QtQuick.Window
import Quickshell
import QtTest
import qs.Commons
import "Plancks" as Plancks
import "PreviewContext.js" as Desktop

ShellRoot {
  id: demo
  property var panel: null
  property var card: null
  property int sceneIndex: -1
  property int sceneFrame: 0
  property int frame: 0
  property int waiting: 0
  property bool saving: false
  property bool entered: false
  property bool actionDone: false
  property string heading: "Your day.\nYour rhythm."
  property string caption: "A second clock, tuned to\nyour daily rhythm."
  property string chapter: "01 / OPPORTUNITY"
  property real pointerX: 930
  property real pointerY: 55
  property real pointerOpacity: 0
  // Editing this sequence changes both the actions and the editorial pacing.
  readonly property var scenes: [
    {seconds: 4, action: "overview", chapter: "01 / OPPORTUNITY", title: "Your day.\nYour rhythm.", copy: "See how much opportunity\nremains in your day."},
    {seconds: 3, action: "configure", chapter: "02 / SESSIONS", title: "Make room\nfor focus.", copy: "Start a Pomodoro session\ninside your epoch."},
    {seconds: 3, action: "start", chapter: "02 / SESSIONS", title: "One stage\nat a time.", copy: "Activity, rest, and repeat.\nYour session has its own clock."},
    {seconds: 2, action: "pause", chapter: "02 / SESSIONS", title: "Take a\nbreather.", copy: "Pause your session\nwhen life interrupts."},
    {seconds: 2, action: "resume", chapter: "02 / SESSIONS", title: "Find your\nmomentum.", copy: "Resume right where\nyou left off."},
    {seconds: 4, action: "history", chapter: "03 / HISTORY", title: "Learn your\npatterns.", copy: "Explore past epochs\nand off-time trends."},
    {seconds: 4, action: "sessionHistory", chapter: "03 / HISTORY", title: "See your\nrhythm build.", copy: "Session trends and daily activity.\nYour recent weeks at a glance."},
    {seconds: 3, action: "settings", chapter: "04 / MAKE IT YOURS", title: "Choose your\ncompanion.", copy: "Sun and moon, Coffee cup,\nStarship, or Roadster."},
    {seconds: 2, action: "starship", chapter: "04 / MAKE IT YOURS", title: "Ready for\nwhat’s next.", copy: "Your rhythm. Your choice."},
    {seconds: 2, action: "roadster", chapter: "04 / MAKE IT YOURS", title: "A little motion.\nYour choice.", copy: "Four companions,\none daily rhythm."},
    {seconds: 3, action: "finish", chapter: "PLANCKS / OMARCHY", title: "Your day.\nYour rhythm.", copy: "A second clock, tuned to\nyour daily rhythm."}
  ]
  readonly property real duration: scenes.reduce(function(sum, scene) { return sum + scene.seconds }, 0)
  QtObject {
    id: bar
    property bool vertical: false
    property int barSize: Style.bar.sizeHorizontal
    property color foreground: Color.foreground
    property color barForeground: Color.foreground
    property color urgent: Color.urgent
    property string position: "top"
    property bool foregroundAnimationEnabled: false
    property bool hidden: false
    property var activePopout: null
    property string fontFamily: Style.font.family
    function requestPopout(item) { activePopout = item }
    function releasePopout(item) { if (activePopout === item) activePopout = null }
    function hideTooltip(item) {}
    function showTooltip(item, text) {}
    function registerClickTarget(item) {}
    function unregisterClickTarget(item) {}
  }
  PanelWindow {
    id: window
    visible: true
    screen: Quickshell.screens.find(function(s) { return s.name === Desktop.screenName })
    implicitWidth: 1280
    implicitHeight: 960
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    Item {
      id: stage
      width: 1280; height: 960
      PreviewWallpaper { id: wallpaper; anchors.fill: parent; overview: true }
      Rectangle { anchors.fill: parent; color: Color.background; opacity: 0.83 }
      Rectangle { x: 64; y: 74; width: 36; height: 3; color: Color.accent }
      Text { x: 116; y: 61; text: "PLANCKS"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: 24; font.letterSpacing: 4 }
      Column {
        x: 64; y: 265; width: 490; spacing: 26
        Text { text: demo.chapter; color: Color.accent; font.family: Style.font.family; font.pixelSize: 15; font.letterSpacing: 2 }
        Text { text: demo.heading; color: Color.foreground; font.family: Style.font.family; font.pixelSize: 56; font.bold: true; lineHeight: 1.12 }
        Text { text: demo.caption; color: Color.muted; font.family: Style.font.family; font.pixelSize: 22; lineHeight: 1.45 }
      }
      Rectangle {
        x: 620; y: 54; width: 600; height: 806; radius: 12
        color: Color.background
        border.color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.14)
        PreviewWallpaper { anchors.fill: parent; anchors.margins: 2; opacity: 0.7 }
      }
      Item {
        id: desktop
        x: 640; y: 74; width: 560; height: 766
        Rectangle {
          width: parent.width; height: bar.barSize; color: Color.bar.background
          Text {
            anchors.right: widget.left; anchors.rightMargin: Style.space(8)
            height: parent.height; verticalAlignment: Text.AlignVCenter
            text: "Thursday 13:37"; color: Color.foreground
            font.family: Style.font.family; font.pixelSize: Style.font.body
          }
          Plancks.Widget {
            id: widget
            anchors.horizontalCenter: parent.horizontalCenter
            bar: bar; width: implicitWidth; height: bar.barSize
            Rectangle {
              anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
              width: widget.openPanelIndicatorWidth; height: 2; radius: 1; color: Color.accent
            }
          }
        }
      }
      Rectangle {
        x: demo.pointerX - 12; y: demo.pointerY - 12; z: 100
        width: 24; height: 24; radius: 12; color: "transparent"
        border.color: Color.accent; border.width: 2; opacity: demo.pointerOpacity
        Behavior on x { NumberAnimation { duration: 260; easing.type: Easing.InOutCubic } }
        Behavior on y { NumberAnimation { duration: 260; easing.type: Easing.InOutCubic } }
        Behavior on opacity { NumberAnimation { duration: 180 } }
        Rectangle { anchors.centerIn: parent; width: 5; height: 5; radius: 3; color: Color.accent }
      }
      Rectangle { x: 64; y: 890; width: 1152; height: 1; color: Color.muted; opacity: 0.25 }
      Text { x: 64; y: 912; text: "REAL INTERFACE  /  SAMPLE HISTORY"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 13; font.letterSpacing: 1.2 }
      Text { x: 940; y: 912; width: 276; horizontalAlignment: Text.AlignRight; text: "gregl83.plancks"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 14 }
      Rectangle { x: 64; y: 890; height: 2; width: 1152 * demo.frame / (demo.duration * DEMO_FPS); color: Color.accent }
      Rectangle {
        anchors.fill: parent; z: 200; color: Color.background
        opacity: demo.frame < DEMO_FPS * 0.5 ? 1 - demo.frame / (DEMO_FPS * 0.5)
          : demo.frame > (demo.duration - 0.5) * DEMO_FPS ? (demo.frame - (demo.duration - 0.5) * DEMO_FPS) / (DEMO_FPS * 0.5) : 0
      }
    }
  }
  TestCase { id: lookup; name: "DemoLookup"; when: false }
  function find(name) {
    var item = name === "plancks_historyButton" && panel ? panel.historyLink
      : lookup.findChild(stage, name) || lookup.findChild(widget, name)
    if (!item) throw new Error("Missing control: " + name)
    return item
  }
  function activate(name) {
    var item = find(name)
    if (!item.visible || !item.enabled) throw new Error("Unavailable control: " + name)
    item.clicked()
  }
  function cue(action) {
    var controls = {configure: "plancks_configureSession", start: "plancks_startSession",
      pause: "plancks_pauseSession", resume: "plancks_pauseSession",
      history: "plancks_historyButton", sessionHistory: "plancks_sessionsTab", starship: "plancks_graphic_starship", roadster: "plancks_graphic_roadster"}
    if (!controls[action]) { pointerOpacity = 0; return }
    var item = find(controls[action])
    var point = item.mapToItem(stage, item.width / 2, item.height / 2)
    pointerX = point.x; pointerY = point.y; pointerOpacity = 0.9
  }
  function enter(action) {
    if (action === "configure") activate("plancks_configureSession")
    else if (action === "start") activate("plancks_startSession")
    else if (action === "pause" || action === "resume") activate("plancks_pauseSession")
    else if (action === "history") activate("plancks_historyButton")
    else if (action === "sessionHistory") activate("plancks_sessionsTab")
    else if (action === "settings") { panel.closeHistory(true); panel.openSettings() }
    else if (action === "starship" || action === "roadster") activate("plancks_graphic_" + action)
    else if (action === "finish") panel.closeSettings()
  }
  function ready(action) {
    var state = Plancks.EpochController.state
    if (Plancks.EpochController.busy || Plancks.EpochController.historyLoading) return false
    if (action === "configure") return panel.showingSession
    if (action === "start" || action === "resume") return state.session && state.session.status !== "paused" && !panel.showingSession
    if (action === "pause") return state.session && state.session.status === "paused"
    if (action === "history") return panel.showingHistory && Plancks.EpochController.history.rows.length > 0
    if (action === "sessionHistory") return panel.showingHistory && panel.sessionHistoryMode
      && !Plancks.EpochController.sessionHistoryLoading && Plancks.EpochController.sessionHistory.rows.length > 0
      && find("plancks_sessionActivity").cells.some(function(cell) { return cell.durationMs > 0 })
    if (action === "settings") return panel.showingSettings
    if (action === "starship" || action === "roadster") return widget.animatedGraphic === action
    if (action === "finish") return !panel.showingSettings && widget.animatedGraphic === "roadster"
    return state.phase === "active" && state.predictedEndUtcMs !== null && state.timer !== "--:--:--"
  }
  function tick() {
    if (saving) return
    if (++waiting > DEMO_FPS * 15) throw new Error("Timed out at scene " + sceneIndex)
    if (!Plancks.EpochController.ready || !wallpaper.ready) return
    if (Plancks.EpochController.error) throw new Error(Plancks.EpochController.error)
    if (!panel) { panel = find("plancks_root"); widget.open(); return }
    if (!card) {
      card = find("plancks_keys").parent.parent
      var popup = find("plancks_popup")
      var scroll = find("plancks_scroll")
      // This staging window includes editorial text; its height is not a bar.
      popup.contentHeight = Qt.binding(function() { return scroll.contentHeight + popup.verticalContentInset })
      card.parent = desktop
      card.transformOrigin = Item.TopLeft
      card.scale = Qt.binding(function() { return Math.min(520 / card.width, 708 / card.height) })
      card.x = Qt.binding(function() { return (desktop.width - card.width * card.scale) / 2 })
      card.y = bar.barSize + Style.gapsOut
      card.opacity = 1
      return
    }
    if (sceneIndex < 0) sceneIndex = 0
    if (sceneIndex >= scenes.length) { console.log("DEMO_PASS frames=" + frame); Qt.quit(); return }
    var scene = scenes[sceneIndex]
    if (!entered) {
      cue(scene.action)
      entered = true
    }
    if (!actionDone && (sceneIndex === 0 || sceneFrame >= Math.round(DEMO_FPS * 0.4))) {
      enter(scene.action)
      heading = scene.title; caption = scene.copy; chapter = scene.chapter
      actionDone = true
      console.log("DEMO_SCENE " + scene.action)
      return
    }
    if (actionDone && !ready(scene.action)) return
    waiting = 0
    if (sceneFrame > DEMO_FPS * 0.7) pointerOpacity = 0
    saving = true
    var path = DEMO_FRAMES + "/" + ("00000" + frame).slice(-5) + ".png"
    if (!stage.grabToImage(function(result) {
      if (!result.saveToFile(path)) { console.error("DEMO_FAIL saving " + path); Qt.quit(); return }
      frame++; sceneFrame++; saving = false
      if (sceneFrame >= Math.round(scene.seconds * DEMO_FPS)) { sceneIndex++; sceneFrame = 0; entered = false; actionDone = false }
    }, Qt.size(Math.round(stage.width / window.devicePixelRatio), Math.round(stage.height / window.devicePixelRatio))))
      throw new Error("Frame capture could not start")
  }
  Timer {
    interval: Math.round(1000 / DEMO_FPS); running: true; repeat: true
    onTriggered: { try { demo.tick() } catch (error) { console.error("DEMO_FAIL " + error); Qt.quit() } }
  }
}
