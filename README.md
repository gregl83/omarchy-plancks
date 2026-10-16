[![Build](https://github.com/gregl83/omarchy-plancks/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/gregl83/omarchy-plancks/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gregl83/omarchy-plancks)](https://github.com/gregl83/omarchy-plancks/releases/latest)
[![Omarchy Plugins](https://img.shields.io/badge/omarchy-plugins-7aa2f7)](https://plugins.omarchy.org/plugin.html?id=gregl83.plancks)
[![Apache 2.0 licensed](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/gregl83/omarchy-plancks/blob/main/LICENSE)

# Plancks

**A second clock, tuned to your daily rhythm.**

<p align="center">
  <a href="assets/demo/plancks.mp4"><img src="assets/demo/plancks.gif" alt="Plancks demo: epoch predictions, starting and pausing a Pomodoro session, history trends, and animation selection" width="960"></a>
</p>

Get a feel for the time ahead. Plancks sits beside your clock in the Omarchy bar, learns your daily rhythm, and estimates when your day will wind down and the next will begin.

An **epoch** is your daily window of opportunity; **off-time** is the space between. Start an epoch when you get up or begin work, and end it when you’re done. Breaks and interruptions are part of the day.

- **See what’s ahead.** A countdown estimates the end of your epoch or the start of your next one.
- **Make time for focus.** Run Pomodoro rounds or your own activity and rest sessions.
- **Find your rhythm.** Browse searchable history and trends, and leave unusual days out of predictions.
- **Pick your companion.** Watch the sun and moon descend through your daily cycle, or a Coffee cup, Starship, or Roadster fill during off-time and empty during your epoch.
- **Get a gentle nudge.** Optional insights and finish notifications help you keep track of your day.
- **Keep it yours.** Local storage, no account, and no network requests from the plugin.

## Install

Requires Omarchy with the Quickshell plugin system and shared `qs.Ui` components, plus Python 3.9+. See the [full requirements](docs/user-guide.md#install) for details.

```bash
omarchy plugin add https://github.com/gregl83/omarchy-plancks.git --enable
omarchy bar move gregl83.plancks --after omarchy.clock
```

That’s it—Plancks appears beside your clock. Click it and select **Start epoch** to begin.

## Your first day with Plancks

Click **Start epoch** when your day begins and **End epoch** when you’re done. At first, the timer counts elapsed time. As Plancks learns from recent days, it begins counting down to your expected finish—and your next start during off-time. You stay in control; estimates never end your day for you.

During an epoch, open **Configure session** beside Settings for Pomodoro rounds or a custom activity timer. Pause when you need to, and move to the next stage when you’re ready. Your timers and history survive sleep and restarts.

Choose Sun and moon, Coffee cup, Starship, or Roadster in **Settings**, and turn on insights or finish notifications if you’d like a nudge. Optional epoch notifications start off.

See the [illustrated user guide](docs/user-guide.md) for screenshots, history, and ways to fine-tune your rhythm.

## Update

```bash
omarchy plugin update gregl83.plancks
omarchy restart shell
```

Your history survives the restart. For local checkouts or uncommitted changes, see [development installation](docs/development-installation.md).

## Remove

```bash
omarchy plugin remove gregl83.plancks
```

Your saved history stays available for a future reinstall. See [removal details](docs/user-guide.md#remove) to delete data or clean up optional keyboard shortcuts.

## Documentation

- [Notifications](docs/notifications.md) — alert variations, message formats, scheduling, and snapshot assets.
- [Animations](docs/animations.md) — each companion’s states, illustrated with representative stills.
- [User guide](docs/user-guide.md) — timer behavior, sessions, settings, shortcuts, and recovery.
- [Migration](docs/migration.md) — bring your history and timers to a new machine.
- [Development installation](docs/development-installation.md) — try local checkouts and uncommitted changes.
- [Development checks](docs/development-checks.md) — run tests and regenerate previews, demos, and notification images.
- [CI and releases](docs/ci-and-releases.md) — automated validation and publishing a release.

## License

[Apache 2.0](LICENSE)
