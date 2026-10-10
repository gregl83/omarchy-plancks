#!/usr/bin/env python3
"""Plancks' journal, daily-window model, and line-oriented QML bridge."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
from datetime import datetime
from functools import cache
import copy
import fcntl
import json
import math
import os
import re
from pathlib import Path
import selectors
import sys
import struct
import tempfile
import time
import uuid

from insights import Insights

VERSION = 1
DEFAULT_ROTATE_BYTES = 5 * 1024 * 1024


def search_terms(text):
    text = re.sub(r"[,\s]+", " ", text.casefold()).strip()
    months = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    return re.findall(rf"\b{months}\s+\d{{1,2}}\b|\b\d{{1,2}}\s+{months}\b|\S+", text)


def history_matches(text, terms):
    # Named dates are phrases; a bare number remains a broad substring search.
    return all(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) if " " in term
               else term in text for term in terms)


def history_search_text(sample, recent):
    """Search the local dates, times, durations, and labels shown in history."""
    excluded = sample["durationMs"] < 0 or sample.get("excludedFromLearning", False)
    fields = ["epoch" if sample["kind"] == "epoch" else "off-time off time",
              "excluded" if excluded else "included",
              "recent sample" if recent else "older"]
    for anchor in (sample["start"], sample["end"]):
        try:
            date = datetime.fromtimestamp(anchor["utcMs"] / 1000).astimezone()
        except (ValueError, OverflowError, OSError):
            continue
        fields.extend([date.strftime("%Y-%m-%d %Y/%m/%d %m/%d/%Y %H:%M:%S %I:%M %p %A %a %b %d %B %d %d %b %d %B"),
                       f"{date.month}/{date.day}/{date.year}",
                       f"{date.strftime('%b')} {date.day} {date.strftime('%B')} {date.day}",
                       f"{date.day} {date.strftime('%b')} {date.day} {date.strftime('%B')}",
                       f"{date.strftime('%b')}{date.day} {date.strftime('%B')}{date.day}",
                       f"{date.hour}:{date.minute:02d}"])
    if sample["durationMs"] < 0:
        fields.append("clock changed backwards")
    else:
        seconds = sample["durationMs"] // 1000
        hours, minutes = divmod(seconds // 60, 60)
        fields.extend([duration(sample["durationMs"]), f"{hours}h {minutes}m", f"{hours}h{minutes}m",
                       f"{hours} hours {minutes} minutes", f"{seconds // 60}m", f"{seconds}s"])
        if seconds < 60:
            fields.append("<1m" if sample["durationMs"] > 0 else "0m")
    return " ".join(search_terms(" ".join(fields)))


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
            "generation": "", "phase": "off", "anchor": None, "lastStart": None, "lastEnd": None,
            "epochId": None, "predictionMs": None, "deadlineUtcMs": None,
            "workSamples": [], "gapSamples": [], "history": [], "warnings": [], "cursor": None}


def apply(state, event):
    # Validate values consumed by the display before accepting a replayed record.
    # Otherwise a syntactically valid but damaged record can masquerade as state.
    stamp = event["clock"]
    if (not isinstance(stamp, dict) or not isinstance(stamp.get("bootId"), str)
            or not stamp["bootId"] or any(type(stamp.get(key)) is not int
            or abs(stamp[key]) > 2**53 - 1 for key in ("utcMs", "bootMs"))):
        raise ValueError("Invalid journal clock")
    prediction = event["predictionMs"]
    if prediction is not None and (type(prediction) not in (int, float)
            or not 1000 <= prediction <= 2**53 - 1):
        raise ValueError("Invalid journal prediction")
    if not isinstance(event["eventId"], str) or not event["eventId"]:
        raise ValueError("Invalid journal event ID")
    if event.get("schemaVersion") != VERSION or event.get("sequence") != state["sequence"] + 1:
        raise ValueError("Unsupported journal version or missing/out-of-order event")
    if event["type"] == "sample_inclusion_changed":
        target = event["sampleId"]
        excluded = event["excludedFromLearning"]
        if not isinstance(target, str) or type(excluded) is not bool:
            raise ValueError("Invalid sample inclusion change")
        sample = next((s for s in state["history"] if s["eventId"] == target), None)
        if sample is None or sample["durationMs"] < 0:
            raise ValueError("Unknown or invalid history interval")
        sample["excludedFromLearning"] = excluded
        rebuild_samples(state)
        state.update(sequence=event["sequence"], lastEventId=event["eventId"],
                     predictionMs=prediction, deadlineUtcMs=event["deadlineUtcMs"])
        return
    starting = event["type"] == "epoch_started"
    if event["type"] not in ("epoch_started", "epoch_ended"):
        raise ValueError("Unknown journal event type")
    if starting != (state["phase"] == "off"):
        raise ValueError("Journal contains an invalid phase transition")
    if not starting and event["epochId"] != state["epochId"]:
        raise ValueError("End event does not match the active epoch")
    sample = event.get("completedSample")
    if sample is not None:
        if (not isinstance(sample, dict) or not isinstance(sample.get("eventId"), str)
                or type(sample.get("durationMs")) not in (int, float)
                or not -(2**53 - 1) <= sample["durationMs"] <= 2**53 - 1):
            raise ValueError("Invalid journal sample")
        if type(sample.get("excludedFromLearning", False)) is not bool:
            raise ValueError("Invalid journal sample exclusion flag")
        sample = dict(sample, kind="off" if starting else "epoch")
        state["history"].append(sample)
        if sample["durationMs"] < 0:
            state["warnings"] = ["The clock moved backwards during an interval. That interval was excluded from predictions."]
        elif not sample.get("excludedFromLearning", False):
            key = "gapSamples" if starting else "workSamples"
            state[key] = (state[key] + [sample])[-5:]
    state.update(sequence=event["sequence"], lastEventId=event["eventId"],
                 phase="active" if starting else "off", anchor=event["clock"],
                 epochId=event["epochId"] if starting else None,
                 predictionMs=event["predictionMs"], deadlineUtcMs=event["deadlineUtcMs"])
    state["lastStart" if starting else "lastEnd"] = event["clock"]


def rebuild_samples(state):
    for kind, key in (("epoch", "workSamples"), ("off", "gapSamples")):
        state[key] = [s for s in state["history"] if s["kind"] == kind
                      and s["durationMs"] >= 0 and not s.get("excludedFromLearning", False)][-5:]


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
        self._generation = ""

    @contextlib.contextmanager
    def locked(self):
        # Never unlink this inode: all helper instances must lock the same object.
        with (self.root / ".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self._finish_reset()
            yield

    def reset_marker(self):
        try:
            marker = json.loads((self.events / ".reset.json").read_text())
            if (not isinstance(marker, dict) or type(marker.get("pending")) is not bool
                    or not isinstance(marker.get("generation"), str)
                    or not 1 <= len(marker["generation"]) <= 128):
                raise ValueError("Invalid reset metadata; restore .reset.json from a backup before continuing")
            self._generation = marker["generation"]
            return marker
        except FileNotFoundError:
            return {"generation": "", "pending": False}

    def _finish_reset(self):
        marker = self.reset_marker()
        if not marker["pending"]:
            return
        # Keep the directory and lock inode stable for other helpers/watchers.
        for path in self.events.glob("events-*.jsonl"):
            path.unlink(missing_ok=True)
        for path in [self.root / "state.json", *self.root.glob(".state-*")]:
            path.unlink(missing_ok=True)
        # Insight delivery metadata is separate from the journal, but belongs
        # to this data reset. Coordinate with an in-flight notification claim.
        insight_lock = self.root / "insights.lock"
        if insight_lock.exists():
            with insight_lock.open("a+b") as stream:
                fcntl.flock(stream, fcntl.LOCK_EX)
                for path in [self.root / "insights.json", *self.root.glob(".insights-*")]:
                    path.unlink(missing_ok=True)
        sync_dir(self.events)
        sync_dir(self.root)
        self.write_json(dict(marker, pending=False), self.events / ".reset.json")
        self._signature, self._cached, self._ids = None, None, {}

    def reset(self, request_id, expected_generation, expected_sequence):
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError("A stable reset ID is required")
        with self.locked():
            marker = self.reset_marker()
            if marker["generation"] == request_id:
                return self.load()  # A retry must never delete newer history.
            if marker["generation"] != expected_generation:
                raise ValueError("Data was reset elsewhere. Review the current state and try again.")
            try:
                state = self.load()
            except (ValueError, KeyError, TypeError):
                state = None  # Explicit reset can recover a damaged journal.
            if state is not None and state["sequence"] != expected_sequence:
                raise ValueError("State changed on another screen. Review the current phase and try again.")
            # Durable intent lets the next lock holder finish an interrupted reset.
            self.write_json({"generation": request_id, "pending": True}, self.events / ".reset.json")
            self._finish_reset()
            state = self.load()
            self.snapshot(state)
            return state

    def load(self):
        """Replay when the journal changes; ordinary ticks reuse the in-memory state."""
        paths = sorted(self.events.glob("events-*.jsonl"))
        generation = self.reset_marker()["generation"]
        signature = (generation,) + tuple((p.name, stat.st_size, stat.st_mtime_ns) for p in paths for stat in [p.stat()])
        if signature == self._signature and self._cached is not None:
            return copy.deepcopy(self._cached)
        state, ids, warnings = blank_state(), {}, []
        state["generation"] = generation
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
                    sample = event.get("completedSample")
                    exclusion = sample.get("excludedFromLearning", False) if sample is not None else None
                    if event["type"] == "sample_inclusion_changed":
                        exclusion = (event["sampleId"], event["excludedFromLearning"])
                    ids[event["eventId"]] = (event["type"], path.name, exclusion)
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
        self.write_json(state, self.root / "state.json")

    def write_json(self, state, destination):
        fd, name = tempfile.mkstemp(prefix=".state-", dir=self.root)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(state, stream, separators=(",", ":"), allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, destination)
            sync_dir(destination.parent)
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
                   rotate_bytes=DEFAULT_ROTATE_BYTES, now=None, expected_generation="",
                   skip_learning=False):
        if type(skip_learning) is not bool:
            raise ValueError("Skip learning must be a boolean")
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
            if state["generation"] != expected_generation:
                raise ValueError("Data was reset. Review the current state and try again.")
            event_type = "epoch_started" if action == "start" else "epoch_ended"
            if event_id in self._ids:
                saved_type, segment, saved_exclusion = self._ids[event_id]
                if saved_type != event_type or (saved_exclusion is not None and saved_exclusion != skip_learning):
                    raise ValueError("Event ID already used for another action")
                # A complete record may only be in the page cache after a failed
                # append fsync. Retry durability before acknowledging it, including
                # after a helper restart, without appending the event again.
                with (self.events / segment).open("rb") as stream:
                    os.fsync(stream.fileno())
                sync_dir(self.events)
                return state, self.snapshot_warning(state)
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
                if action == "end" and state["predictionMs"] is not None:
                    sample["expectedDurationMs"] = state["predictionMs"]
                if skip_learning:
                    sample["excludedFromLearning"] = True
            samples = state["workSamples" if action == "start" else "gapSamples"]
            prediction = estimate(samples, initial_ms if action == "start" else None)
            event = {"schemaVersion": VERSION, "sequence": state["sequence"] + 1,
                     "eventId": event_id, "type": event_type, "clock": now,
                     "epochId": event_id if action == "start" else state["epochId"],
                     "completedSample": sample, "predictionMs": prediction,
                     "deadlineUtcMs": now["utcMs"] + prediction if prediction is not None else None,
                     "predictionSampleIds": [s["eventId"] for s in samples]}
            apply(state, event)
            cursor = self.append(event, rotate_bytes)
            state["cursor"] = cursor
            self._signature = None
            return state, self.snapshot_warning(state)

    def history_page(self, page=0, page_size=5, query=""):
        if type(page) is not int or page < 0:
            raise ValueError("History page must be a nonnegative integer")
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError("History search must be text of at most 256 characters")
        with self.locked():
            state = self.load()
        recent = {s["eventId"] for key in ("workSamples", "gapSamples") for s in state[key]}
        terms = search_terms(query)
        matches = list(reversed(state["history"]))
        if terms:
            filtered = []
            for sample in matches:
                text = history_search_text(sample, sample["eventId"] in recent)
                if history_matches(text, terms):
                    filtered.append(sample)
            matches = filtered
        total = len(matches)
        pages = max(1, math.ceil(total / page_size))
        page = min(page, pages - 1)
        rows = matches[page * page_size:(page + 1) * page_size]
        trends = {}
        for kind in ("epoch", "off"):
            completed = [s for s in state["history"] if s["kind"] == kind and s["durationMs"] >= 0][-10:]
            trends[kind] = [{"eventId": s["eventId"], "endUtcMs": s["end"]["utcMs"],
                             "durationMs": s["durationMs"],
                             "excludedFromLearning": s.get("excludedFromLearning", False)} for s in completed]
        return {"page": page, "pages": pages, "total": total, "sequence": state["sequence"],
                "generation": state["generation"], "trends": trends, "query": query.strip(),
                "unfilteredTotal": len(state["history"]),
                "rows": [dict(s, recent=s["eventId"] in recent) for s in rows]}

    def set_inclusion(self, sample_id, excluded, event_id, expected_sequence,
                      expected_generation="", initial_ms=None, rotate_bytes=DEFAULT_ROTATE_BYTES):
        if type(excluded) is not bool or not isinstance(sample_id, str):
            raise ValueError("Invalid history inclusion command")
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise ValueError("A stable event ID is required")
        if type(rotate_bytes) is not int or rotate_bytes < 1:
            raise ValueError("Rotation size must be a positive integer")
        with self.locked():
            state = self.load()
            if state["generation"] != expected_generation:
                raise ValueError("Data was reset. Review the current history and try again.")
            if event_id in self._ids:
                saved_type, segment, payload = self._ids[event_id]
                if saved_type != "sample_inclusion_changed" or payload != (sample_id, excluded):
                    raise ValueError("Event ID already used for another action")
                with (self.events / segment).open("rb") as stream:
                    os.fsync(stream.fileno())
                sync_dir(self.events)
                return state, self.snapshot_warning(state)
            if expected_sequence != state["sequence"]:
                raise ValueError("State changed on another screen. Review the current history and try again.")
            sample = next((s for s in state["history"] if s["eventId"] == sample_id), None)
            if sample is None or sample["durationMs"] < 0:
                raise ValueError("Unknown or invalid history interval")
            active_key = "workSamples" if state["phase"] == "active" else "gapSamples"
            before = [s["eventId"] for s in state[active_key]]
            sample["excludedFromLearning"] = excluded
            rebuild_samples(state)
            after = [s["eventId"] for s in state[active_key]]
            prediction = state["predictionMs"]
            if before != after:
                prediction = estimate(state[active_key], initial_ms if state["phase"] == "active" else None)
            event = {"schemaVersion": VERSION, "sequence": state["sequence"] + 1,
                     "eventId": event_id, "type": "sample_inclusion_changed", "clock": clock(),
                     "sampleId": sample_id, "excludedFromLearning": excluded,
                     "predictionMs": prediction,
                     "deadlineUtcMs": state["anchor"]["utcMs"] + prediction if prediction is not None else None}
            apply(state, event)
            state["cursor"] = self.append(event, rotate_bytes)
            self._signature = None
            return state, self.snapshot_warning(state)

    def snapshot_warning(self, state):
        try:
            self.snapshot(state)
        except OSError as exc:
            return f"Epoch saved in the journal; state snapshot needs repair: {exc}"
        return None


def live_view(state, now):
    active = state["phase"] == "active"
    elapsed_ms, basis = elapsed(state["anchor"], now) if state["anchor"] else (0, None)
    prediction = state["predictionMs"]
    warnings = list(state["warnings"])
    if elapsed_ms < 0:
        timer, detail = "--:--:--", "Clock changed · prediction unavailable"
        warnings.append("The clock moved backwards between reboots. A prediction is unavailable for this interval.")
    elif prediction is None:
        timer = "+" + duration(elapsed_ms) if state["anchor"] else "--:--:--"
        phase_name = "Epoch" if active else "Off-time"
        detail = phase_name + " elapsed · learning your rhythm" if state["anchor"] else "No prediction yet"
    else:
        # Compare whole elapsed seconds, avoiding an early decrement at start.
        delta = elapsed_ms // 1000 - prediction // 1000
        timer = ("−" if delta < 0 else "+" if delta > 0 else "") + duration(abs(delta) * 1000)
        boundary = "epoch end" if active else "next epoch start"
        detail = ("Until expected " if delta < 0 else "Since expected " if delta > 0 else "At expected ") + boundary
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
                       "generation": state["generation"],
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
        return bool(self.state["anchor"])


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
    insights = Insights(store.root)
    insights_error = ""

    def emit(result):
        print(json.dumps(result, separators=(",", ":")), flush=True)

    def insight_failure(exc):
        nonlocal insights_error
        insights.failed = True
        message = "Insights unavailable: " + str(exc)
        if message != insights_error:
            insights_error = message
            emit({"ok": True, "insightsError": message})

    def refresh():
        nonlocal display
        with store.locked():
            state = store.load()
        display = Display(state, initial_ms)
        try:
            age = elapsed(state["anchor"], clock())[0] if state["anchor"] else 0
            insights.sync(state, age)
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            insight_failure(exc)
        if persistent_warning:
            display.state = dict(state, warnings=state["warnings"] + [persistent_warning])

    def publish(full=False, request_id=None):
        nonlocal last_sent
        if display is None:
            return
        now = clock()
        values = display.update(now)
        if not insights.failed:
            try:
                age = elapsed(display.state["anchor"], now)[0] if display.state["anchor"] else 0
                message = insights.tick(age, now)
                if message:
                    emit({"ok": True, "insight": message})
            except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
                insight_failure(exc)
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
        nonlocal initial_ms, persistent_warning, panel_open, display, insights_error
        ack = request.get("requestId")
        try:
            action = request["action"]
            if action == "configure":
                value = request.get("initialSeconds", 0)
                if (type(value) not in (int, float)
                        or not (value == 0 or 1 <= value <= (2**53 - 1) / 1000)):
                    raise ValueError("Initial duration must be 0 (learn first) or at least one second, within the supported clock range")
                initial_ms = value * 1000 if value > 0 else None
                if insights.configure(request) and insights_error:
                    insights_error = ""
                    emit({"ok": True, "insightsError": ""})
            elif action == "panel":
                if not isinstance(request.get("open"), bool):
                    raise ValueError("Panel open must be a boolean")
                panel_open = request["open"]
            elif action == "preview_insight":
                if display is None:
                    raise ValueError("Load history before previewing an insight")
                age = elapsed(display.state["anchor"], clock())[0] if display.state["anchor"] else 0
                emit({"ok": True, "insight": insights.preview(display.state, age)})
                return
            elif action == "history":
                emit({"ok": True, "history": store.history_page(request.get("page", 0), query=request.get("query", "")), "requestId": ack})
                return
            elif action == "set_inclusion":
                _, persistent_warning = store.set_inclusion(
                    request["sampleId"], request["excludedFromLearning"], request["requestId"],
                    request["sequence"], request.get("generation", ""), initial_ms,
                    request.get("rotateBytes", DEFAULT_ROTATE_BYTES))
            elif action == "reset":
                store.reset(request["requestId"], request["generation"], request["sequence"])
                persistent_warning = None
            elif action in ("start", "end"):
                _, persistent_warning = store.transition(action, request["requestId"], request["sequence"],
                                                          initial_ms, request.get("rotateBytes", DEFAULT_ROTATE_BYTES),
                                                          expected_generation=request.get("generation", ""),
                                                          skip_learning=request.get("skipLearning", False))
            else:
                raise ValueError("Unknown command")
            # Disk validation is reserved for commands and filesystem events.
            refresh()
            publish(full=True, request_id=ack)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            emit({"ok": False, "error": str(exc), "retryable": isinstance(exc, OSError), "requestId": ack,
                  "generation": store._generation})
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
        except (OSError, ValueError, KeyError, TypeError) as exc:
            persistent_warning = f"State snapshot unavailable: {exc}"
        try:
            refresh()
            publish(full=True)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            emit({"ok": False, "error": str(exc), "generation": store._generation})
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
                            if any(display.values.get(k) != last_sent.get(k) for k in ("generation", "sequence", "phase", "warnings")):
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
    parser.add_argument("--skip", action="store_true", help="Exclude the completed interval from prediction learning")
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
                                                  args.sequence, args.initial_seconds * 1000 or None,
                                                  expected_generation=state["generation"], skip_learning=args.skip)
            print(json.dumps({"ok": True, "view": view(state), "warning": warning}))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
