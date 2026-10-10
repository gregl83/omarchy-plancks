"""Local insight catalog and active-epoch scheduler. No background threads or polling."""
from __future__ import annotations

import contextlib
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import tempfile

MINUTE = 60_000
HOUR = 60 * MINUTE
CADENCE = {"light": (3 * HOUR, 4 * HOUR), "standard": (2 * HOUR, 3 * HOUR),
           "frequent": (HOUR, 2 * HOUR)}
GRACE = 90_000
COOLDOWN = 2 * MINUTE

# Meaning IDs are independent of wording IDs. Changing the sentence must not
# make the same observation eligible again.
ENCOURAGEMENT = {
    "momentum": ("Good momentum. Keep building.", "Still moving forward. Keep that going.",
                 "You've got momentum. Stay with it.", "A little momentum goes a long way."),
    "next_step": ("One useful next step. That's enough to keep moving.", "Choose one thing. Give it a good run.",
                  "Small steps count. So does this one.", "One clear next step can change the shape of the day."),
    "possibility": ("There's room for something good here.", "Your next good idea still has room to happen.",
                    "A useful window. Plenty of possibility.", "There's still something worth starting."),
    "direction": ("Keep what matters in sight.", "A clear direction. One step at a time.",
                  "You get to choose what comes next.", "Pick the next useful thing. Keep it simple."),
    "building": ("Keep building. Small things add up.", "Steady steps make substantial things.",
                 "A little more forward. That's how things grow.", "Good things can take shape one step at a time."),
    "confidence": ("You've got this. Keep going.", "A good moment to trust your next step.",
                   "Keep going. There's something here.", "You have room to make this count."),
    "credit": ("Give yourself credit for showing up.", "You made room for this. That counts.",
               "Another window of opportunity. Good to have you here.", "Showing up is a solid beginning."),
    "simple": ("Simple is useful. Start there.", "One thing at a time. Still an excellent system.",
               "Keep the next step small and clear.", "A manageable next step is a good next step."),
    "curiosity": ("A good moment to follow a promising idea.", "There's room to try something worthwhile.",
                  "One useful experiment could open things up.", "Stay curious. Something good may follow."),
    "steady": ("Steady is a strength.", "Keep your rhythm. Let the small things accumulate.",
               "Consistency has a quiet kind of power.", "Steady forward. A dependable approach."),
    "elapsed": ("{hours} hours into your epoch. You've got momentum.",
                "{hours} hours in. Keep your next step in sight.",
                "{hours} hours on the clock. Still room to make it count.",
                "{hours} hours of opportunity. Keep building."),
    "overrun_time": ("An extra {extra}. Still going strong.", "{extra} beyond the prediction. Solid momentum.",
                     "An extra {extra}. Apparently, you had more in you.",
                     "{extra} into extra time. You're keeping it going."),
}
OVERRUN = ("Expected finish exceeded. You're killing it.", "Past the prediction. Still going strong.",
           "Extra time. Solid momentum.", "You had more in you. Clearly.",
           "Beyond your expected finish. Still building.", "The prediction ended. Your momentum didn't.")
WARNINGS = ("{remaining} to your expected finish. Finish strong.",
            "About {remaining} remaining. Make it count.",
            "{remaining} to your projected finish. One more useful step.",
            "{remaining} left in your expected window. Bring it home strong.")
ONE_MINUTE = ("One minute to your expected finish. Make it count.",
              "One minute remaining. One final spark.",
              "Your expected finish is a minute away. Finish strong.",
              "One minute to the prediction. Keep that momentum.")
STATS = {
    "start_consistency": ("Your last five starts span {span}, down from {previous}. Your rhythm is tightening.",
                          "Start-time spread: {span}, previously {previous}. Getting more consistent.",
                          "Your recent starts are closer together: {span} versus {previous}. Steady rhythm."),
    "duration_consistency": ("Your last five epoch lengths span just {span}. A steady rhythm.",
                             "Five epoch lengths within {span} of one another. Consistency looks good.",
                             "Recent epoch lengths are within {span}. Your rhythm is taking shape."),
    "milestone": ("{count} included epochs completed. That's consistency.",
                  "{count} completed, included epochs in the log. A substantial rhythm.",
                  "{count} included epochs recorded. Keep building."),
    "month_hours": ("Over {hours} hours of included opportunity recorded this month. A substantial window.",
                    "This month's included epochs add up to more than {hours} hours. Room for a lot of possibility.",
                    "More than {hours} hours of opportunity in this month's log. Steady accumulation."),
    "duration_record": ("You've passed your longest included epoch this month. New ground.",
                        "Your longest included epoch this month, surpassed. You're still going strong.",
                        "A new duration mark for this month. Apparently, you had more in you."),
    "earlier_start": ("Today's start was earlier than your previous ten included starts. A head start.",
                      "Earlier than your previous ten included starts. Good beginning.",
                      "Earlier than your previous ten starts. A little extra room today."),
    "forecast_accuracy": ("{matches} of your last five eligible finishes were within 30 minutes of the forecast. Getting dialed in.",
                          "Forecast check: {matches} of five eligible finishes within 30 minutes. A rhythm is forming.",
                          "{matches} of five eligible finishes landed within 30 minutes of their prediction. Steady signal."),
    "morning_pattern": ("Your last five starts this week were before 09:00. A steady beginning.",
                        "Five recent starts this week, all before 09:00. Consistency looks good.",
                        "Before 09:00 on each of your last five starts this week. Rhythm established."),
}


def normalize_settings(values):
    values = values if isinstance(values, dict) else {}
    frequency = values.get("insightFrequency", "standard")
    if frequency not in CADENCE:
        frequency = "standard"
    raw = values.get("finishWarningSeconds", [1800, 60])
    if not isinstance(raw, list) or not 1 <= len(raw) <= 6 or any(
            type(v) not in (int, float) or not math.isfinite(v) or not 1 <= v <= 86400 for v in raw):
        raw = [1800, 60]
    return {"enabled": values.get("insightsEnabled") is True,
            "finish": values.get("finishNotificationsEnabled") is True,
            "frequency": frequency, "warnings": sorted({round(v) for v in raw}, reverse=True)}


def length(ms):
    if ms < MINUTE:
        if ms <= 0:
            return "less than a minute"
        seconds = max(1, round(ms / 1000))
        return f"{seconds} second" + ("s" if seconds != 1 else "")
    minutes = max(1, round(ms / MINUTE))
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{minutes} minute" + ("s" if minutes != 1 else "")
    text = f"{hours} hour" + ("s" if hours != 1 else "")
    return text + (f" {rest} minutes" if rest else "")


def local(ms):
    return datetime.fromtimestamp(ms / 1000).astimezone()


def circular_span(minutes):
    points = sorted(minutes)
    gaps = [b - a for a, b in zip(points, points[1:])] + [points[0] + 1440 - points[-1]]
    return 1440 - max(gaps)


def fact_key(kind, samples):
    payload = ":".join(s["eventId"] for s in samples)
    return kind + ":" + hashlib.sha256(payload.encode()).hexdigest()[:16]


class Statistics:
    """One history pass per revision; notifications only inspect cached aggregates."""
    def __init__(self):
        self.revision = None
        self.builds = 0
        self.fixed = []
        self.month_max = None
        self.current_month = None

    def update(self, state):
        revision = (state["generation"], state["sequence"])
        if revision == self.revision:
            return
        self.revision = revision
        self.builds += 1
        self.fixed = []
        self.month_max = None
        anchor = state.get("lastStart") or state.get("anchor")
        if not anchor:
            return
        current = local(anchor["utcMs"])
        month = (current.year, current.month)
        self.current_month = month
        epochs = [s for s in state["history"] if s["kind"] == "epoch" and s["durationMs"] >= 0
                  and not s.get("excludedFromLearning", False)]
        starts = [(s, local(s["start"]["utcMs"])) for s in epochs]
        if len(epochs) >= 10:
            recent = starts[-5:]
            previous = starts[-10:-5]
            span = circular_span([d.hour * 60 + d.minute for _, d in recent])
            before = circular_span([d.hour * 60 + d.minute for _, d in previous])
            if before >= 10 and span <= before * 0.75:
                self.fixed.append(("start_consistency", fact_key("starts", [s for s, _ in recent + previous]),
                                   {"span": length(span * MINUTE), "previous": length(before * MINUTE)}))
        if len(epochs) >= 5:
            last = epochs[-5:]
            span = max(s["durationMs"] for s in last) - min(s["durationMs"] for s in last)
            if span <= HOUR:
                self.fixed.append(("duration_consistency", fact_key("durations", last), {"span": length(span)}))
        if len(epochs) in (10, 25, 50, 100, 250, 500, 1000):
            self.fixed.append(("milestone", f"milestone:{len(epochs)}", {"count": len(epochs)}))
        this_month = [s for s, d in starts if (d.year, d.month) == month]
        total = sum(s["durationMs"] for s in this_month)
        bucket = int(total / (10 * HOUR)) * 10
        if bucket >= 20 and total > bucket * HOUR:
            self.fixed.append(("month_hours", f"month:{current.year}-{current.month}:{bucket}", {"hours": bucket}))
        if len(this_month) >= 3:
            self.month_max = max(s["durationMs"] for s in this_month)
        if len(starts) >= 10 and state["phase"] == "active":
            latest = [d.hour * 60 + d.minute for _, d in starts[-10:]]
            now_minute = current.hour * 60 + current.minute
            if 180 <= now_minute < min(latest) and all(180 <= m <= 840 for m in latest):
                self.fixed.append(("earlier_start", "early:" + str(state.get("epochId")), {}))
        forecasts = [s for s in epochs if type(s.get("expectedDurationMs")) in (int, float)
                     and math.isfinite(s["expectedDurationMs"]) and s["expectedDurationMs"] >= 1000][-5:]
        if len(forecasts) == 5:
            matches = sum(abs(s["durationMs"] - s["expectedDurationMs"]) <= 30 * MINUTE for s in forecasts)
            if matches >= 4:
                self.fixed.append(("forecast_accuracy", fact_key("forecasts", forecasts), {"matches": matches}))
        week = current.isocalendar()[:2]
        week_starts = [(s, d) for s, d in starts if d.isocalendar()[:2] == week]
        if state["phase"] == "active":
            week_starts.append(({"eventId": state["epochId"]}, current))
        if len(week_starts) >= 5 and all(d.hour < 9 for _, d in week_starts[-5:]):
            self.fixed.append(("morning_pattern", fact_key("mornings", [s for s, _ in week_starts[-5:]]), {}))

    def candidates(self, state, age):
        result = list(self.fixed)
        if age > 3 * HOUR:
            result = [c for c in result if c[0] != "earlier_start"]
        # An epoch crossing a local month boundary is not compared with a
        # different month's record. No history scan is needed to reject it.
        if (state["phase"] == "active" and self.month_max is not None and age > self.month_max + MINUTE
                and (local(state["anchor"]["utcMs"] + age).year,
                     local(state["anchor"]["utcMs"] + age).month) == self.current_month):
            result.append(("duration_record", "record:" + str(state["epochId"]), {}))
        return result


class Insights:
    def __init__(self, root, rng=None):
        self.path = Path(root) / "insights.json"
        self.rng = rng or random.Random()
        self.config = normalize_settings({})
        self.stats = Statistics()
        self.book = None
        self.preview_book = self.blank()
        self.state = None
        self.next_check = math.inf
        self.last_age = None
        self.failed = False

    @staticmethod
    def blank():
        return {"schemaVersion": 1, "generation": "", "epoch": "", "delivered": [], "next": None,
                "lastNotice": None, "recentFacts": [], "recentMessages": [], "recentKinds": []}

    def read(self):
        try:
            book = json.loads(self.path.read_text())
        except (FileNotFoundError, ValueError):
            return self.blank()
        if (not isinstance(book, dict) or book.get("schemaVersion") != 1
                or any(not isinstance(book.get(k), list) or any(not isinstance(v, str) for v in book[k])
                       for k in ("delivered", "recentFacts", "recentMessages", "recentKinds"))
                or not isinstance(book.get("epoch"), str) or not isinstance(book.get("generation"), str)
                or any(book.get(k) is not None and (type(book[k]) not in (int, float)
                       or not math.isfinite(book[k]) or book[k] < 0) for k in ("next", "lastNotice"))):
            return self.blank()
        return book

    @contextlib.contextmanager
    def locked(self):
        with self.path.with_suffix(".lock").open("a+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def save(self):
        fd, name = tempfile.mkstemp(prefix=".insights-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(self.book, stream, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def interval(self):
        return self.rng.randint(*CADENCE[self.config["frequency"]])

    def configure(self, values):
        config = normalize_settings(values)
        changed = config != self.config
        self.config = config
        if changed:
            self.failed = False
            self.last_age = None
            self.next_check = 0
        return changed

    def targets(self):
        prediction = self.state.get("predictionMs") if self.state else None
        if prediction is None:
            return []
        result = []
        if self.config["finish"]:
            result += [(f"warning:{seconds}", prediction - seconds * 1000, seconds)
                       for seconds in self.config["warnings"]]
        if self.config["enabled"]:
            result.append(("overrun", prediction + 90_000, None))
        return result

    def update_next(self):
        if not self.book or not self.state or self.state["phase"] != "active":
            self.next_check = math.inf
            return
        targets = [target for key, target, _ in self.targets() if key not in self.book["delivered"]]
        if self.config["enabled"] and self.book["next"] is not None:
            targets.append(self.book["next"])
        self.next_check = min(targets, default=math.inf)

    def sync(self, state, age):
        self.state = state
        if self.failed or not (self.config["enabled"] or self.config["finish"]):
            self.next_check = math.inf
            return
        if self.config["enabled"]:
            self.stats.update(state)
        # Reset metadata invalidates insight history even while off-time is quiet.
        if self.book and self.book["generation"] != state["generation"]:
            with self.locked():
                self.book = self.blank()
                self.book["generation"] = state["generation"]
                self.save()
        if state["phase"] != "active" or age < 0:
            self.next_check = math.inf
            self.last_age = None
            return
        with self.locked():
            book = self.read()
            dirty = False
            if book["generation"] != state["generation"]:
                book = self.blank()
                book["generation"] = state["generation"]
                dirty = True
            if book["epoch"] != state["epochId"]:
                book.update(epoch=state["epochId"], delivered=[], next=None)
                dirty = True
            self.book = book
            # No retroactive warning when enabling, restarting or changing a
            # prediction. Existing delivery IDs still prevent duplicate alerts.
            for key, target, _ in self.targets():
                if target <= age and key not in book["delivered"]:
                    book["delivered"].append(key)
                    dirty = True
            if self.config["enabled"] and (book["next"] is None or book["next"] <= age):
                first = 90 * MINUTE + self.rng.randint(0, 15 * MINUTE)
                book["next"] = first if age < first else age + self.interval()
                dirty = True
            if dirty:
                self.save()
        self.last_age = age
        self.update_next()

    def choose(self, age, preview=False):
        book = self.book or self.blank()
        candidates = [c for c in self.stats.candidates(self.state, age) if c[1] not in book["recentFacts"]]
        fresh = [c for c in candidates if c[0] not in book["recentKinds"][-4:]]
        candidates = fresh or candidates
        meanings = list(ENCOURAGEMENT)
        if age < 3 * HOUR:
            meanings.remove("elapsed")
        prediction = self.state.get("predictionMs")
        if prediction is None or age - prediction < HOUR:
            meanings.remove("overrun_time")
        meanings = [k for k in meanings if k not in book["recentKinds"][-4:]] or ["momentum"]
        # Most opportunities favor a factual observation when one is eligible.
        if candidates and self.rng.random() < 0.65:
            kind, fact, fields = self.rng.choice(candidates)
            pool = STATS[kind]
        else:
            kind = self.rng.choice(meanings)
            fact = "encouragement:" + kind
            fields = {"hours": max(1, int(age / HOUR)), "extra": length(age - (prediction or age))}
            pool = ENCOURAGEMENT[kind]
        return self.phrase(kind, fact, fields, pool, preview)

    def phrase(self, kind, fact, fields, pool, preview=False):
        recent = (self.book or self.blank())["recentMessages"]
        options = [(f"{kind}:{i}", text) for i, text in enumerate(pool) if f"{kind}:{i}" not in recent]
        if not options:
            options = [(f"{kind}:{i}", text) for i, text in enumerate(pool)]
        message_id, template = self.rng.choice(options)
        return {"message": template.format(**fields), "kind": kind, "fact": fact, "messageId": message_id,
                "preview": preview}

    def preview(self, state, age):
        self.stats.update(state)
        saved_state, saved_book = self.state, self.book
        if self.preview_book["generation"] != state["generation"]:
            self.preview_book = self.blank()
            self.preview_book["generation"] = state["generation"]
        self.state, self.book = state, self.preview_book
        try:
            # Preview history is session-local and independent of real delivery.
            # Sampling a fact must not consume it for scheduled notifications.
            message = self.choose(max(0, age) if state["phase"] == "active" else 0, preview=True)
            for field, value, limit in (("recentFacts", message["fact"], 100),
                                        ("recentMessages", message["messageId"], 30),
                                        ("recentKinds", message["kind"], 12)):
                self.preview_book[field] = (self.preview_book[field] + [value])[-limit:]
            return message
        finally:
            self.state, self.book = saved_state, saved_book

    def tick(self, age, now):
        if (self.failed or not self.state or self.state["phase"] != "active" or age < 0
                or not (self.config["enabled"] or self.config["finish"])):
            return None
        gap = self.last_age is not None and age - self.last_age > 15_000
        self.last_age = age
        if age < self.next_check and not gap:
            return None
        with self.locked():
            self.book = self.read()
            if self.book["epoch"] != self.state["epochId"] or self.book["generation"] != self.state["generation"]:
                return None  # A different helper/reset owns the current schedule.
            dirty, message = False, None
            due = []
            for key, target, seconds in self.targets():
                if key in self.book["delivered"] or age < target:
                    continue
                if gap or age - target > GRACE or target < 0:
                    self.book["delivered"].append(key)
                    dirty = True
                else:
                    due.append((key, target, seconds))
            last = self.book["lastNotice"]
            cooling = last is not None and 0 <= now["utcMs"] - last < COOLDOWN
            if due and not cooling:
                key, _, seconds = max(due, key=lambda t: t[1])
                self.book["delivered"].append(key)
                dirty = True
                if seconds is None:
                    message = self.phrase("overrun", "overrun:" + self.state["epochId"], {}, OVERRUN)
                else:
                    message = self.phrase(key, key + ":" + self.state["epochId"],
                                          {"remaining": length(seconds * 1000)}, ONE_MINUTE if seconds == 60 else WARNINGS)
            occasional_due = self.config["enabled"] and self.book["next"] is not None and age >= self.book["next"]
            if occasional_due:
                upcoming = [target for key, target, _ in self.targets()
                            if key not in self.book["delivered"] and age <= target <= age + 5 * MINUTE]
                if not gap and message is None and not cooling and not upcoming:
                    message = self.choose(age)
                self.book["next"] = age + self.interval()
                dirty = True
            if message:
                self.book["lastNotice"] = now["utcMs"]
                for field, value, limit in (("recentFacts", message["fact"], 100),
                                            ("recentMessages", message["messageId"], 30),
                                            ("recentKinds", message["kind"], 12)):
                    self.book[field] = (self.book[field] + [value])[-limit:]
            if dirty:
                # Claim before emitting. A crash can lose a toast, but cannot
                # repeat it on restart or through a second helper.
                self.save()
        self.update_next()
        if cooling and self.next_check <= age:
            self.next_check = age + max(1, last + COOLDOWN - now["utcMs"])
        return message
