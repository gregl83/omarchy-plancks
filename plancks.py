#!/usr/bin/env python3
"""Plancks' journal, daily-window model, and line-oriented QML bridge."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
from functools import cache
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import selectors
import sys
import struct
import tempfile
import time
import uuid

VERSION = 1
DEFAULT_ROTATE_BYTES = 5 * 1024 * 1024


@cache
def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def clock():
    return {"utcMs": time.time_ns() // 1_000_000,
            "bootId": boot_id(),
            "bootMs": time.clock_gettime_ns(time.CLOCK_BOOTTIME) // 1_000_000}


def elapsed(start, end):
    same_boot = start["bootId"] == end["bootId"]
    key = "bootMs" if same_boot else "utcMs"
    return end[key] - start[key], "boottime" if same_boot else "utc-fallback"


def estimate(samples, fallback=None):
    values = sorted(sample["durationMs"] for sample in samples[-5:])
    if not values:
        return fallback
    if len(values) >= 3:
        values = values[1:-1]
    return max(1000, math.floor(sum(values) / len(values) / 1000 + 0.5) * 1000)


def duration(milliseconds):
    seconds = max(0, int(milliseconds) // 1000)
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def blank_state():
    return {"schemaVersion": VERSION, "sequence": 0, "lastEventId": None,
            "phase": "off", "anchor": None, "lastStart": None, "lastEnd": None,
            "epochId": None, "predictionMs": None, "deadlineUtcMs": None,
            "workSamples": [], "gapSamples": [], "warnings": [], "cursor": None}


def apply(state, event):
    if event.get("schemaVersion") != VERSION or event.get("sequence") != state["sequence"] + 1:
        raise ValueError("Unsupported journal version or missing/out-of-order event")
    starting = event["type"] == "epoch_started"
    if event["type"] not in ("epoch_started", "epoch_ended"):
        raise ValueError("Unknown journal event type")
    if starting != (state["phase"] == "off"):
        raise ValueError("Journal contains an invalid phase transition")
    if not starting and event["epochId"] != state["epochId"]:
        raise ValueError("End event does not match the open epoch")
    sample = event.get("completedSample")
    if sample:
        if sample["durationMs"] < 0:
            state["warnings"] = ["A negative clock interval was excluded from predictions."]
        else:
            key = "gapSamples" if starting else "workSamples"
            state[key] = (state[key] + [sample])[-5:]
    state.update(sequence=event["sequence"], lastEventId=event["eventId"],
                 phase="active" if starting else "off", anchor=event["clock"],
                 epochId=event["epochId"] if starting else None,
                 predictionMs=event["predictionMs"], deadlineUtcMs=event["deadlineUtcMs"])
    state["lastStart" if starting else "lastEnd"] = event["clock"]


def state_root():
    configured = os.environ.get("XDG_STATE_HOME", "")
    base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".local/state"
    return base / "omarchy/gregl83.plancks"


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else state_root()
        self.events = self.root / "events"
        self.events.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._signature = None
        self._cached = None
        self._ids = {}

    @contextlib.contextmanager
    def locked(self):
        # Never unlink this inode: all helper instances must lock the same object.
        with (self.root / ".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def load(self):
        """Replay when the journal changes; ordinary ticks reuse the in-memory state."""
        paths = sorted(self.events.glob("events-*.jsonl"))
        signature = tuple((p.name, stat.st_size, stat.st_mtime_ns) for p in paths for stat in [p.stat()])
        if signature == self._signature and self._cached is not None:
            return copy.deepcopy(self._cached)
        state, ids, warnings = blank_state(), {}, []
        for number, path in enumerate(paths, 1):
            if path.name != f"events-{number:08d}.jsonl":
                raise ValueError("Missing or unexpected journal segment; restore the event history before continuing")
            with path.open("rb") as stream:
                for line in stream:
                    if not line.endswith(b"\n"):
                        warnings.append(f"Preserved incomplete tail in {path.name}.")
                        break
                    try:
                        event = json.loads(line)
                        if event["eventId"] in ids:
                            raise ValueError("Duplicate journal event ID")
                        apply(state, event)
                    except (ValueError, KeyError, TypeError) as exc:
                        raise ValueError(f"Invalid record in {path.name}: {exc}") from exc
                    ids[event["eventId"]] = event["type"]
                    state["cursor"] = {"segment": path.name, "offset": stream.tell()}
        try:
            snapshot = json.loads((self.root / "state.json").read_text())
        except (OSError, ValueError):
            snapshot = None
        if (isinstance(snapshot, dict) and snapshot.get("schemaVersion") == VERSION
                and isinstance(snapshot.get("sequence"), int)
                and snapshot["sequence"] > state["sequence"]):
            raise ValueError("Journal ends before the saved snapshot; restore missing event history before continuing")
        state["warnings"] += warnings
        self._signature, self._cached, self._ids = signature, copy.deepcopy(state), ids
        return state

    def snapshot(self, state):
        fd, name = tempfile.mkstemp(prefix=".state-", dir=self.root)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(state, stream, separators=(",", ":"), allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.root / "state.json")
            sync_dir(self.root)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def recover(self):
        with self.locked():
            state = self.load()
            # History is small (normally two events/day); validate the entire journal
            # on startup instead of trusting a potentially stale checkpoint.
            try:
                existing = json.loads((self.root / "state.json").read_text())
            except (OSError, ValueError):
                existing = None
            if existing != state:
                self.snapshot(state)
            return state

    def append(self, event, rotate_bytes):
        payload = (json.dumps(event, separators=(",", ":"), allow_nan=False) + "\n").encode()
        paths = sorted(self.events.glob("events-*.jsonl"))
        path = paths[-1] if paths else self.events / "events-00000001.jsonl"
        rotate = False
        if path.exists() and path.stat().st_size:
            with path.open("rb") as stream:
                stream.seek(-1, os.SEEK_END)
                rotate = stream.read(1) != b"\n"
            rotate = rotate or path.stat().st_size + len(payload) > rotate_bytes
        if rotate:
            path = self.events / f"events-{len(paths) + 1:08d}.jsonl"
        with path.open("ab") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            offset = stream.tell()
        sync_dir(self.events)
        return {"segment": path.name, "offset": offset}

    def transition(self, action, event_id, expected_sequence, initial_ms=None,
                   rotate_bytes=DEFAULT_ROTATE_BYTES, now=None):
        if action not in ("start", "end"):
            raise ValueError("Action must be start or end")
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise ValueError("A stable event ID is required")
        if initial_ms is not None and (not isinstance(initial_ms, (int, float)) or
                                       not math.isfinite(initial_ms) or initial_ms < 1000):
            raise ValueError("Initial duration must be at least one second or null")
        if not isinstance(rotate_bytes, int) or rotate_bytes < 1:
            raise ValueError("Rotation size must be a positive integer")
        with self.locked():
            state = self.load()
            event_type = "epoch_started" if action == "start" else "epoch_ended"
            if event_id in self._ids:
                if self._ids[event_id] != event_type:
                    raise ValueError("Event ID already used for another action")
                return state, None
            if expected_sequence != state["sequence"]:
                raise ValueError("State changed on another screen. Review the current phase and try again.")
            if (action == "start") != (state["phase"] == "off"):
                raise ValueError("That phase transition has already happened")
            now = now or clock()
            sample = None
            if state["anchor"]:
                length, basis = elapsed(state["anchor"], now)
                sample = {"eventId": event_id, "start": state["anchor"], "end": now,
                          "durationMs": length, "timeBasis": basis}
            samples = state["workSamples" if action == "start" else "gapSamples"]
            prediction = estimate(samples, initial_ms if action == "start" else None)
            event = {"schemaVersion": VERSION, "sequence": state["sequence"] + 1,
                     "eventId": event_id, "type": event_type, "clock": now,
                     "epochId": event_id if action == "start" else state["epochId"],
                     "completedSample": sample, "predictionMs": prediction,
                     "deadlineUtcMs": now["utcMs"] + prediction if prediction is not None else None,
                     "predictionSampleIds": [s["eventId"] for s in samples]}
            cursor = self.append(event, rotate_bytes)
            apply(state, event)
            state["cursor"] = cursor
            warning = None
            try:
                self.snapshot(state)
            except OSError as exc:
                warning = f"Epoch saved in the journal; state snapshot needs repair: {exc}"
            self._signature = None
            return state, warning


def live_view(state, now):
    active = state["phase"] == "active"
    elapsed_ms, basis = elapsed(state["anchor"], now) if state["anchor"] else (0, None)
    prediction = state["predictionMs"]
    warnings = list(state["warnings"])
    if elapsed_ms < 0:
        timer, detail = "--:--:--", "Clock changed · prediction unavailable"
        warnings.append("Clock moved backwards across boots; this interval cannot be predicted reliably.")
    elif prediction is None:
        timer = "+" + duration(elapsed_ms) if active else "--:--:--"
        detail = "Learning daily window · elapsed time" if active else "No prediction yet"
    else:
        # Compare whole elapsed seconds, avoiding an early decrement at start.
        delta = elapsed_ms // 1000 - prediction // 1000
        timer = ("−" if delta < 0 else "+" if delta > 0 else "") + duration(abs(delta) * 1000)
        boundary = "end" if active else "start"
        detail = ("Time until predicted " if delta < 0 else "Past predicted " if delta > 0 else "At predicted ") + boundary
    return {"timer": timer, "status": ("Epoch active" if active else "Off-time") + " · " + detail,
            "elapsed": duration(elapsed_ms), "timeBasis": basis, "warnings": warnings}


def forecasts(state, now, work, gap):
    elapsed_ms, _ = elapsed(state["anchor"], now) if state["anchor"] else (0, None)
    prediction = state["predictionMs"]
    deadline = now["utcMs"] + prediction - elapsed_ms if prediction is not None and elapsed_ms >= 0 else None
    active = state["phase"] == "active"
    next_start = (deadline + gap if gap is not None and deadline is not None else None) if active else deadline
    next_end = deadline if active else (next_start + work if next_start is not None and work is not None else None)
    return {"predictedEndUtcMs": next_end, "predictedStartUtcMs": next_start}


class Display:
    """Immutable epoch data and learned estimates, with small clock-only updates."""
    def __init__(self, state, initial_ms=None, now=None):
        self.state = state
        self.work = estimate(state["workSamples"], initial_ms)
        self.gap = estimate(state["gapSamples"])
        active = state["phase"] == "active"
        self.values = {"phase": state["phase"], "sequence": state["sequence"],
                       "indicator": "●" if active else "○",
                       "lastStartUtcMs": state["lastStart"]["utcMs"] if state["lastStart"] else None,
                       "lastEndUtcMs": state["lastEnd"]["utcMs"] if state["lastEnd"] else None,
                       "workPredictionMs": state["predictionMs"] if active else self.work,
                       "gapPredictionMs": self.gap if active else state["predictionMs"],
                       "workSampleCount": len(state["workSamples"]), "gapSampleCount": len(state["gapSamples"])}
        self.offset = None
        self.update(now or clock())

    def update(self, now):
        # Wall/boot offset only moves materially on a clock correction. Avoid
        # jittering forecast timestamps (and QML bindings) by a millisecond/tick.
        offset = now["utcMs"] - now["bootMs"]
        was_invalid = self.values.get("timer") == "--:--:--"
        self.values.update(live_view(self.state, now))
        is_invalid = self.values["timer"] == "--:--:--"
        if self.offset is None or abs(offset - self.offset) >= 1000 or was_invalid != is_invalid:
            self.values.update(forecasts(self.state, now, self.work, self.gap))
            self.offset = offset
        return self.values

    def ticking(self, panel_open):
        return bool(self.state["anchor"] and (self.state["phase"] == "active"
                    or self.state["predictionMs"] is not None or panel_open))


def view(state, now=None, initial_ms=None):
    return Display(state, initial_ms, now).values


class JournalWatch:
    """One inotify fd in the existing event loop; no polling or watcher process."""
    # Watch completed writes and directory changes, never reads/opens. In
    # particular, watching lock-file closes would cause a self-wakeup loop.
    MASK = 0x00000008 | 0x00000040 | 0x00000080 | 0x00000100 | 0x00000200 | 0x00000400 | 0x00000800

    def __init__(self, directory):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.inotify_init1.argtypes = [ctypes.c_int]
        libc.inotify_init1.restype = ctypes.c_int
        libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        libc.inotify_add_watch.restype = ctypes.c_int
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "Cannot watch epoch history")
        if libc.inotify_add_watch(self.fd, os.fsencode(directory), self.MASK) < 0:
            error = ctypes.get_errno()
            self.close()
            raise OSError(error, "Cannot watch epoch history")

    def close(self):
        os.close(self.fd)

    def drain(self):
        changed = False
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return changed
            offset = 0
            while offset < len(data):
                _, mask, _, length = struct.unpack_from("iIII", data, offset)
                offset += 16 + length
                if mask & (0x400 | 0x800 | 0x8000):
                    raise ValueError("Epoch history directory was moved or removed; restore it and reconnect")
                # Includes IN_Q_OVERFLOW: force a fresh replay if any changes
                # were dropped rather than trusting the previous cache.
                changed = True


def serve(store):
    initial_ms, display = None, None
    persistent_warning = None
    panel_open = False
    last_sent = {}
    buffer = b""

    def emit(result):
        print(json.dumps(result, separators=(",", ":")), flush=True)

    def refresh():
        nonlocal display
        with store.locked():
            state = store.load()
        display = Display(state, initial_ms)
        if persistent_warning:
            display.state = dict(state, warnings=state["warnings"] + [persistent_warning])

    def publish(full=False, request_id=None):
        nonlocal last_sent
        if display is None:
            return
        values = display.update(clock())
        if full:
            result = {"ok": True, "view": dict(values)}
            last_sent = dict(values)
        else:
            keys = ["timer", "status", "warnings"]
            if panel_open:
                keys += ["elapsed", "timeBasis", "predictedEndUtcMs", "predictedStartUtcMs"]
            changes = {key: values[key] for key in keys if values[key] != last_sent.get(key)}
            if not changes:
                return
            result = {"ok": True, "patch": changes}
            last_sent.update(changes)
        if request_id is not None:
            result["requestId"] = request_id
        emit(result)

    def respond(request):
        nonlocal initial_ms, persistent_warning, panel_open, display
        ack = request.get("requestId")
        try:
            action = request["action"]
            if action == "configure":
                value = request.get("initialSeconds", 0)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError("Initial duration must be a nonnegative number of seconds")
                initial_ms = value * 1000 if value > 0 else None
            elif action == "panel":
                if not isinstance(request.get("open"), bool):
                    raise ValueError("Panel open must be a boolean")
                panel_open = request["open"]
            elif action in ("start", "end"):
                _, persistent_warning = store.transition(action, request["requestId"], request["sequence"],
                                                          initial_ms, request.get("rotateBytes", DEFAULT_ROTATE_BYTES))
            else:
                raise ValueError("Unknown command")
            # Disk validation is reserved for commands and filesystem events.
            refresh()
            publish(full=True, request_id=ack)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            emit({"ok": False, "error": str(exc), "retryable": isinstance(exc, OSError), "requestId": ack})
            try:
                refresh()
                publish(full=True)
            except (OSError, ValueError, KeyError, TypeError):
                display = None  # Do not keep advertising stale state as usable.

    # Watch before recovery so a concurrent writer cannot fall between the
    # initial snapshot and subscription. Close both fds on every exit path.
    with contextlib.closing(JournalWatch(store.events)) as watcher, selectors.DefaultSelector() as selector:
        selector.register(sys.stdin, selectors.EVENT_READ, "command")
        selector.register(watcher.fd, selectors.EVENT_READ, "journal")
        try:
            store.recover()
        except OSError as exc:
            persistent_warning = f"State snapshot unavailable: {exc}"
        refresh()
        publish(full=True)
        while True:
            timeout = 1 if display is not None and display.ticking(panel_open) else None
            events = selector.select(timeout=timeout)
            if not events:
                publish()
                continue
            for key, _ in events:
                if key.data == "journal":
                    if watcher.drain():
                        store._signature = None
                        try:
                            refresh()
                            # A different writer may have changed phase/anchors.
                            if any(display.values.get(k) != last_sent.get(k) for k in ("sequence", "phase", "warnings")):
                                publish(full=True)
                        except (OSError, ValueError, KeyError, TypeError) as exc:
                            display = None
                            emit({"ok": False, "error": str(exc)})
                    continue
                chunk = os.read(sys.stdin.fileno(), 65536)
                if not chunk:
                    return
                buffer += chunk
                if len(buffer) > 1024 * 1024:
                    raise ValueError("Command exceeds size limit")
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        request = json.loads(line)
                        if not isinstance(request, dict):
                            raise ValueError("Command must be an object")
                    except ValueError as exc:
                        emit({"ok": False, "error": str(exc)})
                        continue
                    respond(request)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("serve", "status", "start", "end"), nargs="?", default="status")
    parser.add_argument("--state-dir", type=Path, help="Use isolated storage (for development/tests)")
    parser.add_argument("--request-id", default=None)
    parser.add_argument("--sequence", type=int, help="Expected sequence for start/end")
    parser.add_argument("--initial-seconds", type=int, default=0)
    args = parser.parse_args()
    try:
        store = Store(args.state_dir)
        if args.action == "serve":
            serve(store)
        else:
            state = store.recover()
            warning = None
            if args.action != "status":
                if args.sequence is None:
                    parser.error("start/end requires --sequence from status")
                state, warning = store.transition(args.action, args.request_id or str(uuid.uuid4()),
                                                  args.sequence, args.initial_seconds * 1000 or None)
            print(json.dumps({"ok": True, "view": view(state), "warning": warning}))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
