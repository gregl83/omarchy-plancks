# Plancks

Plancks is an Omarchy bar widget for your daily opportunity window. Standard clocks keep people in sync; Plancks helps you understand your own daily rhythm.

An **epoch** is your window of available opportunity; **off-time** is the interval between epochs. Start an epoch when you get out of bed or sign in to work, and end it when you go to bed or sign out—usually once each per day.

Plancks learns from recent epochs and off-time intervals to predict when your current epoch will end and when the next one will start. The window includes normal breaks and interruptions; it measures available opportunity, not continuous productive effort.

The widget renders Planck-time notation as italic **t** with an upright subscript capital **P**, equivalent to `t_P`. Durations are ordinary hours, minutes, and seconds.

The bar uses normal text for an active epoch and Omarchy's standard dimmed styling for off-time. The tooltip, accessible label, and panel name the phase explicitly.

| Appearance | Example | Meaning |
| --- | --- | --- |
| Normal | `t_P −02:00:00` | Two hours until the current epoch is expected to end |
| Normal | `t_P +00:15:00` | The current epoch is still active, fifteen minutes after its expected end time |
| Dimmed | `t_P −02:00:00` | Two hours until the next epoch is expected to start |
| Dimmed | `t_P +00:15:00` | The next epoch has not started, and its expected start time was fifteen minutes ago |

The timer descriptions use **Until expected epoch end** / **Since expected epoch end** while an epoch is active, and **Until expected next epoch start** / **Since expected next epoch start** during off-time.

Starting or ending an epoch changes its active/off-time appearance; passing an expected time does not. Resetting also returns the widget to off-time. Storage errors show an undimmed `!` marker. Click the widget to open its panel, then use **Start epoch** / **End epoch**. The panel shows actual timestamps, elapsed time, expected durations, and the next expected start/end. Tab moves between buttons, and Enter or Space activates the focused button. With focus on the panel itself, Enter or Space starts or ends an epoch (or retries a storage error). Escape closes the panel, or cancels an open reset confirmation.

## Install

Requires an Omarchy release with the Quickshell plugin system and shared `qs.Ui` components, plus Python 3. The plugin uses only Python's standard library. It does not support the older Waybar shell.

Install through Omarchy:

```bash
omarchy plugin add https://github.com/gregl83/omarchy-plancks.git --enable
omarchy bar move gregl83.plancks --after omarchy.clock
```

Omarchy creates the plugin directory, clones the repository, validates it, and enables the widget. Plancks creates its runtime storage automatically. There are no directories to create manually. The manifest defaults to the center section; the second command places the widget immediately after the clock.

### Try a local checkout without publishing

After committing the plugin files locally, run these commands from the repository:

```bash
omarchy plugin add "$PWD" --enable
omarchy bar move gregl83.plancks --after omarchy.clock
```

Omarchy clones the local Git repository, so only committed files are included. Nothing is published. To pull subsequent local commits into that installed copy:

```bash
omarchy plugin update gregl83.plancks
```

### Test uncommitted development changes

From the repository directory, validate and copy the runtime files to try edits without committing:

```bash
omarchy plugin validate .
mkdir -p ~/.config/omarchy/plugins/gregl83.plancks
cp manifest.json qmldir Widget.qml EpochPanel.qml EpochController.qml plancks.py \
  ~/.config/omarchy/plugins/gregl83.plancks/
omarchy-shell shell rescanPlugins
omarchy plugin enable gregl83.plancks --after omarchy.clock
```

Repeat the copy step after editing. QML widget and panel changes hot-reload, but the shared controller and its long-running Python helper can survive plugin rescans. After changing `plancks.py` or `EpochController.qml`, restart the shell to load the new code:

```bash
omarchy restart shell
```

This briefly reloads the desktop shell; the saved epoch and its timing survive the restart. This manual copy method is for development. A copy-only installation receives updates by copying again, rather than through Git.

## Learning your daily rhythm

With no history and the default settings, the first epoch counts up from `+00:00:00`. Here `+` means elapsed time since starting; once a prediction exists, it means time since the expected epoch end. The tooltip and panel show “Epoch elapsed · learning your rhythm” while no epoch prediction is available. Off-time shows `--:--:--` until an off-time interval has been recorded and the next epoch ends. That is when the first off-time prediction takes effect.

For each prediction, Plancks uses up to five recent completed intervals of that kind. With five samples, it drops one shortest and one longest and averages the remaining three. Epoch and off-time histories are independent. With one or two samples, it uses their mean; with three or four, it drops the extremes and averages what remains. Predictions round to whole seconds with a one-second minimum.

A daily window of 07:00–23:00 teaches a 16-hour epoch duration. Starting again at 07:00 teaches eight hours of off-time. A workday sign-in/sign-out routine learns its own durations with the same model.

While active, the next-start forecast uses the expected end plus expected off-time. Ending the epoch anchors that forecast to the actual end. The current phase's expected duration stays fixed until you start or end an epoch, including after shell reloads. Late starts and overruns do not change phase automatically.

Settings live inline on the widget's entry in Omarchy's `shell.json`. To supply an initial eight-hour epoch estimate before any history exists:

```bash
omarchy bar set gregl83.plancks initialSeconds 28800 --json
```

The default `initialSeconds` is `0` (learn first). Changing it affects future starts without history; it does not change an active epoch. The optional `rotateBytes` setting defaults to `5242880` (5 MiB).

## Optional keyboard shortcut

While the widget is enabled and loaded, start or end an epoch without opening its panel:

```bash
omarchy-shell gregl83.plancks toggleEpoch
```

The command uses the same **Start epoch** / **End epoch** action as the panel. It returns `submitted` when the action is sent to storage, `busy` while an action is pending, or `not-ready` when storage is loading or unavailable. `submitted` does not mean the action has been saved yet. Any storage failure appears in the widget and panel, where you can select **Retry**.

To assign **Super+Alt+P**, first check for conflicts with `omarchy menu keybindings --print`, then add this optional binding to `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + ALT + P", "Plancks: Start/end epoch", "omarchy-shell gregl83.plancks toggleEpoch")
```

Choose an unused combination, or explicitly unbind an existing assignment before replacing it. Validate the configuration with `hyprctl reload` and `hyprctl configerrors`. The plugin installer does not install keybindings automatically. After updating the controller in an existing installation, run `omarchy restart shell` to register the new IPC action.

## Reset all data

Open the widget panel and select **Reset all data…**. A warning explains what will be deleted; **Cancel** is focused by default. Select **Delete all data and reset** to permanently delete recorded epochs, off-time intervals, and learned predictions and discard any active epoch. Escape cancels the confirmation. Reset cannot be undone; back up the [storage directory](#persistence-and-recovery) first if you want to keep your history.

The widget returns to its initial off-time state and learns again from new epochs. Widget settings (`initialSeconds`, `rotateBytes`, and bar placement) stay intact. Reset is also available when damaged history prevents starting or ending an epoch. Other instances of the widget refresh automatically.

## Persistence and recovery

Runtime history lives at `$XDG_STATE_HOME/omarchy/gregl83.plancks/`, falling back to `~/.local/state/omarchy/gregl83.plancks/`. A relative XDG path is ignored.

- `events/events-00000001.jsonl`, etc.: append-only start/end records, rotated before the next record exceeds the segment limit. All segments are retained until you reset the data. One record may exceed a very small configured limit.
- `state.json`: the single mutable snapshot, replaced atomically after a durable journal append. Includes phase, clock anchors, frozen prediction, recent samples, and replay position.
- `events/.reset.json`: a reset token and completion flag, containing no epoch history. It prevents stale commands and duplicate reset retries from deleting new history and allows interrupted deletion to finish on recovery.
- `.lock`: an empty coordination file for serializing helper instances; it contains no epoch state.

The journal is authoritative. Plancks replays and validates it on startup or when its files change, then caches the result in memory. A missing or damaged snapshot is rebuilt. An incomplete final record is preserved and the next append goes into a new segment. Malformed complete records or missing segments block updates and display an error. Back up the entire directory together; ordinary journal recovery never deletes history. Once a reset is confirmed, recovery finishes any interrupted deletion.

Ordinary one-second updates use cached state and predictions: they do not scan, read, lock, or write history files. An in-process Linux inotify watch detects journal changes without another watcher process. The helper sends only changed timer/status fields; elapsed details update while a panel is open. Before there is any running display to update, it sleeps until a command or file change. Multiple monitor widgets share a controller, and storage also locks and checks revisions to reject stale commands. If storage fails, the panel reports the failure and offers **Retry**; retries reuse the request ID to avoid recording an action twice.

Elapsed time includes suspend and uses Linux's suspend-inclusive monotonic clock within a boot. Across reboots it falls back to UTC timestamps; a backwards interval is flagged and excluded from learning. An active epoch stays active through suspend, shutdown, and midnight until you end it or reset the data. Long absences, including weekends, are included in off-time samples. Plancks has no automatic schedule, correction for a forgotten epoch end, or history editor.

## Development checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
python3 tests/smoke_qml.py
```

The QML smoke check needs an active Wayland session and the installed Omarchy shell. It uses temporary storage and does not change the live bar. Add `--preview` to briefly show the test widget and panel. It checks two widgets sharing epoch state through IPC, busy/not-ready guards, overrun, vertical layout, and reset. Physical suspend/reboot and manual keyboard interaction still warrant a live-session check.

## License

[Apache 2.0](LICENSE)
