# omarchy-plancks

An Omarchy bar widget showing your general daily opportunity window. Start an epoch when you get out of bed or sign into work, and end it when you go to bed or sign out—usually once each per day.

Plancks learns from recent daily windows to predict opportunity remaining and the off-time before your next start. The window includes normal breaks and interruptions; it measures available opportunity, not continuous productive effort.

The widget renders Planck-time notation as italic **t** with an upright subscript capital **P**, equivalent to `t_P`. Durations are ordinary hours, minutes, and seconds.

The bar uses normal text for an active epoch and Omarchy's standard dimmed styling for off-time. The tooltip, accessible label, and panel name the phase explicitly.

| Appearance | Example | Meaning |
| --- | --- | --- |
| Normal | `t_P −02:00:00` | Epoch active; two hours until its predicted end |
| Normal | `t_P +00:15:00` | Epoch active; fifteen minutes past its predicted end |
| Dimmed | `t_P −02:00:00` | Off-time; two hours until the predicted next start |
| Dimmed | `t_P +00:15:00` | Off-time; fifteen minutes past the predicted next start |

Only starting or ending an epoch changes its active/off-time appearance. Storage errors show an undimmed `!` marker. Click the widget to open its panel, then use **Start epoch** / **End epoch**. The panel shows actual timestamps, elapsed time, predicted durations, and the next expected start/end. Enter or Space activates the primary action; Escape closes the panel.

## Install

Requires an Omarchy release with the Quickshell plugin system and shared `qs.Ui` components, plus Python 3. The plugin uses only Python's standard library. It does not support the older Waybar shell.

Once the implementation is pushed to this repository, install it through Omarchy:

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

To try working-tree edits without committing, copy the runtime files instead:

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

With no history, the first epoch counts up from `+00:00:00`. Here `+` means elapsed time since starting; once a prediction exists, it means time past the predicted end. The tooltip and panel identify the first epoch as learning your daily window. Off-time shows `--:--:--` until a complete end-to-next-start interval has been recorded.

For each prediction, select the last five completed intervals of that kind, drop one shortest and one longest, and average the remaining three. Work and off-time histories are independent. During warm-up, one or two samples use their mean; three or four drop the extremes first. Predictions round to whole seconds with a one-second minimum.

A daily window of 07:00–23:00 teaches a 16-hour opportunity duration. Starting again at 07:00 teaches eight hours of off-time. A workday sign-in/sign-out routine learns its own durations with the same model.

While active, the next-start forecast uses the predicted end plus predicted off-time. Ending the epoch anchors that forecast to the actual end. The current phase's predicted duration stays fixed until your next Start/End action, including after shell reloads. Late starts and overruns do not change phase automatically.

Settings live inline on the widget's entry in Omarchy's `shell.json`. To supply an initial eight-hour opportunity estimate before any history exists:

```bash
omarchy bar set gregl83.plancks initialSeconds 28800 --json
```

The default `initialSeconds` is `0` (learn first). Changing it affects future starts without history; it does not rewrite an open epoch. The optional `rotateBytes` setting defaults to `5242880` (5 MiB).

## Persistence and recovery

Runtime history lives at `$XDG_STATE_HOME/omarchy/gregl83.plancks/`, falling back to `~/.local/state/omarchy/gregl83.plancks/`. A relative XDG path is ignored.

- `events/events-00000001.jsonl`, etc.: append-only start/end records, rotated before the next record exceeds the segment limit. All segments are retained. One record may exceed a very small configured limit.
- `state.json`: the single mutable snapshot, replaced atomically after a durable journal append. Includes phase, clock anchors, frozen prediction, recent samples, and replay position.
- `.lock`: an empty coordination file for serializing helper instances; it contains no epoch state.

The journal is authoritative. This first pass replays and validates it on startup or when its files change, then caches the result in memory. A missing or damaged snapshot is rebuilt. An incomplete final record is preserved and the next append goes into a new segment. Malformed complete records or missing segments block updates and display an error. Back up the entire directory together; recovery never deletes history.

Ordinary one-second updates use cached state and predictions: they do not scan, read, lock, or write history files. An in-process Linux inotify watch detects journal changes without another watcher process. The helper sends only changed timer/status fields; elapsed details update while a panel is open. Before there is any running display to update, it sleeps until a command or file change. Multiple monitor widgets share a controller, and storage also locks and checks revisions to reject stale commands. If storage fails, the panel reports the failure and offers Retry; retries reuse the event ID to avoid recording an action twice.

Elapsed time includes suspend and uses Linux's suspend-inclusive monotonic clock within a boot. Across reboots it falls back to UTC timestamps; a backwards interval is flagged and excluded from learning. An open epoch remains open through suspend, shutdown, and midnight until you explicitly end it. Long absences, including weekends, are included in off-time samples. This first pass has no automatic schedule, forgotten-sign-out correction, or history editor.

## Development checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
python3 tests/smoke_qml.py
```

The QML smoke check needs an active Wayland session and the installed Omarchy shell. It uses temporary storage and does not change the live bar. Add `--preview` to briefly show the test widget and panel. It checks two widgets sharing Start/End state, overrun, and vertical layout. Physical suspend/reboot and manual keyboard interaction still warrant a live-session check.

## License

[Apache 2.0](LICENSE)
