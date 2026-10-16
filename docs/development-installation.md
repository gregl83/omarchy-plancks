# Development installation

## Try a local checkout without publishing

After committing the plugin files locally, run these commands from the repository:

```bash
omarchy plugin add "$PWD" --enable
omarchy bar move gregl83.plancks --after omarchy.clock
```

Omarchy clones the local Git repository, so only committed files are included. Nothing is published. To pull subsequent local commits into that installed copy:

```bash
omarchy plugin update gregl83.plancks
```

## Test uncommitted development changes

From the repository directory, validate and copy the runtime files to try edits without committing:

```bash
omarchy plugin validate .
mkdir -p ~/.config/omarchy/plugins/gregl83.plancks
cp manifest.json qmldir Widget.qml EpochPanel.qml EpochController.qml HistoryView.qml HistoryTrend.qml AnimatedGraphic.qml CoffeeGraphic.qml StarshipGraphic.qml SunMoonGraphic.qml RoadsterGraphic.qml GraphicPreview.qml InsightsSettings.qml Graphics.js plancks.py insights.py sessions.py SessionConfig.qml SessionHistory.qml SessionActivity.qml BoundedTextField.qml clipboard_read.py notification_send.py \
  ~/.config/omarchy/plugins/gregl83.plancks/
cp -r assets ~/.config/omarchy/plugins/gregl83.plancks/
omarchy-shell shell rescanPlugins
omarchy plugin enable gregl83.plancks --after omarchy.clock
```

Repeat the copy step after editing. QML widget and panel changes hot-reload, but the shared controller and its long-running Python helper can survive plugin rescans. After changing `plancks.py`, `insights.py`, or `EpochController.qml`, restart the shell to load the new code:

```bash
omarchy restart shell
```

This briefly reloads the desktop shell; the saved epoch and its timing survive the restart. This manual copy method is for development. A copy-only installation receives updates by copying again, rather than through Git.
