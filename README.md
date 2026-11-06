[![Build](https://github.com/gregl83/omarchy-plancks/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/gregl83/omarchy-plancks/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gregl83/omarchy-plancks)](https://github.com/gregl83/omarchy-plancks/releases/latest)
[![Omarchy Plugins](https://img.shields.io/badge/omarchy-plugins-7aa2f7)](https://plugins.omarchy.org/plugin.html?id=gregl83.plancks)
[![Apache 2.0 licensed](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/gregl83/omarchy-plancks/blob/main/LICENSE)

# Plancks

**A second clock, tuned to your daily rhythm.**

<p align="center">
  <a href="assets/demo/plancks.mp4"><img src="assets/demo/plancks.gif" alt="Plancks demo: epoch predictions, starting and pausing a Pomodoro session, history trends, and animation selection" width="960"></a>
</p>

Plancks is a daily rhythm and focus timer for the Omarchy bar. It learns when your day usually ends and the next begins, with optional Pomodoro sessions and a desktop countdown.

- **See what’s ahead.** Estimates adapt to your recent days; you decide when to start and stop.
- **Make time for focus.** Use Pomodoro rounds or custom activity and rest intervals.
- **Find your rhythm.** Explore history and trends, and exclude unusual days from predictions.
- **Make it yours.** Choose Sun and moon, Coffee cup, Starship, or Roadster, plus optional glass countdowns and notifications.

**Local storage. No account. No network requests from the plugin.**

## Install

Requires Omarchy’s Quickshell plugin system and Python 3.9+. Older Waybar-based installations are not supported. [Full requirements](docs/user-guide.md#install).

```bash
omarchy plugin add https://github.com/gregl83/omarchy-plancks.git --enable
omarchy bar move gregl83.plancks --after omarchy.clock
```

Plancks appears beside your clock. Click it and select **Start epoch** to begin.

## Start your first day

An **epoch** is your day or workday; **off-time** is the gap between. Select **Start epoch** when you begin and **End epoch** when you’re done. Initially, Plancks shows elapsed time. As it learns your rhythm, it counts down to your expected finish or next start. Estimates never end your day automatically.

Use **Configure session** for Pomodoro or custom activity/rest intervals. Timers and history survive sleep and restarts. In **Settings**, choose an animation or enable the optional overlay and notifications; the overlay and epoch notifications start off.

## Optional Super-key shortcuts

Control Plancks without reaching for the mouse:

| Shortcut | Action |
| --- | --- |
| **Super+Alt+P** | Start/end an epoch, or handle the current session stage. |
| **Super+Alt+Shift+P** | Skip an epoch boundary and exclude that interval from predictions. |

Check for conflicts with `omarchy menu keybindings --print`, then add these to `~/.config/hypr/bindings.lua` using unused key combinations:

```lua
o.bind("SUPER + ALT + P", "Plancks: Epoch / next stage", "omarchy-shell gregl83.plancks primaryAction")
o.bind("SUPER + ALT + SHIFT + P", "Plancks: Skip epoch", "omarchy-shell gregl83.plancks toggleEpochSkip")
```

Apply and check:

```bash
hyprctl reload
hyprctl configerrors
```

These shortcuts are optional and are not installed automatically. See [session-aware shortcut behavior](docs/user-guide.md#optional-keyboard-shortcut) for actions and confirmations.

## Update

```bash
omarchy plugin update gregl83.plancks
omarchy restart shell
```

Your history and settings are preserved.

## Remove

To also erase your history, use **Settings → Reset all data…** before uninstalling. Otherwise, it stays available for a future reinstall.

```bash
omarchy plugin remove gregl83.plancks
```

If you added the shortcuts above, remove those two lines from `~/.config/hypr/bindings.lua`, then run `hyprctl reload` and `hyprctl configerrors`. [Removal details](docs/user-guide.md#remove).

## Documentation

- [User guide](docs/user-guide.md) — screenshots, sessions, settings, history, and recovery.
- [Animations](docs/animations.md) · [Notifications](docs/notifications.md) — visual states and alert options.
- [Migration](docs/migration.md) — move your history and timers to another machine.
- Contributing: [local installation](docs/development-installation.md) · [tests and previews](docs/development-checks.md) · [CI and releases](docs/ci-and-releases.md).

## License

[Apache 2.0](LICENSE)
