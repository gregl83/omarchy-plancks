# Move Plancks to a new machine

Bring your history with you and pick up where you left off. Plancks keeps its data locally, so migration is a copy of its storage directory.

## What to copy

Copy the **entire `gregl83.plancks` directory**, including hidden files:

```text
~/.local/state/omarchy/gregl83.plancks/
```

If you set an absolute `$XDG_STATE_HOME`, the directory is `$XDG_STATE_HOME/omarchy/gregl83.plancks/` instead. Check the location on each machine; they can differ.

This carries over epoch and session history, inclusion choices, the history used for predictions, and active or paused timers. Keep all files together: `state.json` alone is not a backup. The `events/` directory is the authoritative history.

## Transfer your data

1. Install the same Plancks version on the new machine using the [installation instructions](../README.md#install). You can update after confirming the transfer worked. Older versions may not understand newer history formats.
2. Stop the Omarchy shell on both machines before copying, and leave it stopped until the transfer is complete. This prevents Plancks from changing data during the copy. You can transfer files from a text console or another login while the desktop shell is stopped.
3. Make a backup of the source directory. If the new machine already has Plancks data, move that directory aside as a separate backup. Restore into an empty destination rather than combining histories.
4. Transfer the whole directory using a file manager, archive, or file-copy tool that includes hidden files. Place it under the new user’s state directory so the result is `omarchy/gregl83.plancks/events/`, without an extra nested `gregl83.plancks` folder. Ensure the new user owns and can write the copied files.
5. Start the Omarchy shell on the new machine. Open Plancks and check **View history**, the current epoch, and any session. Keep your source backup until everything looks right.

Continue recording on the new machine. Copies on separate machines do not synchronize or merge later.

## How timers resume

An active epoch stays active. An unpaused session includes the time spent transferring, just as it would after a restart; a paused session stays paused. Pause a session before migration if you want to exclude transfer time from that session’s activity. Pausing a session does not pause its epoch.

Across machines, elapsed time uses UTC timestamps, so keep both system clocks accurate. History is displayed in the new machine’s local time zone.

## Desktop preferences

Bar placement, keyboard shortcuts, and widget configuration in Omarchy’s `shell.json` are separate from the history directory. Reapply those preferences on the new machine, or transfer only the relevant Plancks configuration. Avoid replacing the new machine’s entire desktop configuration just to move Plancks.

For storage errors, backup details, and version compatibility, see [Persistence and recovery](user-guide.md#persistence-and-recovery).
