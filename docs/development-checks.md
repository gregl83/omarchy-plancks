# Development checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
python3 tests/smoke_qml.py
python3 tests/smoke_roadster.py
```

The QML smoke check needs an active Wayland session and the installed Omarchy shell. It uses temporary storage and does not change the live bar. Add `--preview` to briefly show the test widget and panel. It checks two widgets sharing epoch state through IPC, busy/not-ready guards, normal and skip transitions, overrun, vertical layout, and reset. With `--preview` (also used in CI), it exercises history navigation, inclusion switches, pagination, trends and their empty-state behavior, plus the reset warning, default Cancel focus, Cancel activation, Escape cancellation, and explicit deletion through keyboard input. The same suite also covers draft validation/cancellation, saved session settings, shared state, pause/resume, situational primary actions, repeat suppression, paused-overrun guards, closed-panel epoch confirmation/cancellation, atomic skip closure, session detail navigation, and recovered overrun/final completion. Storage tests cover suspend-inclusive clocks and restart recovery; physical suspend/reboot still warrant a live-session check.

Regenerate the panel previews in `assets/` and the root marketplace showcase with `python3 scripts/preview.py` in an active Omarchy session. It renders the production panels with isolated, frozen sample history, uses the active theme’s wallpaper, colors, and font, and leaves your saved history untouched. Backgrounds use the focused monitor’s logical dimensions and Omarchy’s centered aspect-preserving crop; panel captures retain desktop scale, while the showcase scales the desktop uniformly to fit its composition. The wide showcase at `preview.png` presents the epoch timer, history, graphics, and Pomodoro/custom session capabilities together. `scripts/showcase.py` can regenerate it independently from the existing panel capture. The current Omarchy marketplace discovers this root-level `preview.png` automatically; the manifest has no supported preview-path field.

Rebuild the animated demo in an active Omarchy Wayland session:

```bash
python3 scripts/demo.py
```

Requires Quickshell with QtTest, the installed Omarchy shell, and FFmpeg with the `libx264` encoder. The command writes `assets/demo/plancks.mp4` (1280×960, 20 fps), `plancks.gif` (960×720, 15 fps, looping), and `poster.png`. It renders the current production QML, seeds temporary sample history, and drives named controls through predictions, Pomodoro configuration, start/pause/resume, epoch history, session trends and daily activity, and graphic selection. The 30-second sequence uses the active theme and wallpaper. The sample clock starts on a fixed date and ticks normally; relative date labels share that reference date. Frame counts and scene timing are fixed, while animation phases and clock seconds can vary slightly with capture speed. Personal history and saved widget settings are untouched, and notifications are disabled.

Edit the `scenes` array in `scripts/demo.qml` to change captions, durations, or action order; `enter()`, `cue()`, and `ready()` define actions, pointer targets, and completion conditions. Missing controls, failed transitions, storage errors, or capture failures stop the build; details are saved in `assets/demo/render.log`. Reordering actions must preserve their prerequisites (for example, start a session before pausing it). Use `--output-dir /tmp/plancks-demo` for alternate renders, `--fps 30` for a smoother MP4, or `--keep-frames` to inspect the PNG sequence. `PLANCKS_PREVIEW_CONTEXT` supports the same desktop context JSON as the static preview renderer. Run the command after UI changes and inspect the results before committing refreshed media.

Install ImageMagick for transparent-margin trimming. Regenerate notification images with `python3 scripts/notification_assets.py`. Use a white foreground so exported stills retain the graphic’s intended contrast and per-element transparency. This renders the production QML graphics offscreen into `assets/notifications/{sun-moon,coffee,starship,roadster}/`, with matching `active`, `off-time`, `learning`, and `overtime` folders. Each still is trimmed to its visible bounds, proportionally fitted within 108 × 108 pixels, and centered on a transparent 116 × 116 canvas for the notification’s square icon slot.

All current and future animated graphics **must horizontally center their complete visible silhouette within their canvas**, including handles, bases, flames, and other attachments. Use the midpoint of the full rendered horizontal bounds, not just the main body or control points. Maintain this alignment through every state and animation frame; allow at most one rendered pixel of rasterization error. Correct the drawing itself, never compensate with offsets in the panel or settings previews. Notification exports separately crop and fit each still to the square icon slot. Verify transparent-image bounds across states and regenerate notification assets after geometry changes.
