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
from statistics import median
import tempfile

MINUTE = 60_000
HOUR = 60 * MINUTE
CADENCE = {"light": (3 * HOUR, 4 * HOUR), "standard": (2 * HOUR, 3 * HOUR),
           "frequent": (HOUR, 2 * HOUR)}
GRACE = 90_000
COOLDOWN = 2 * MINUTE

# Meaning IDs are independent of wording IDs. Changing the sentence must not
# make the same observation eligible again.
# Verified short excerpts; keep sources with the catalog and in docs/notifications.md.
QUOTES = {'jobs': ('Your time is limited, so don’t waste it living someone else’s life.',
          'Steve Jobs',
          'https://news.stanford.edu/stories/2005/06/steve-jobs-2005-graduates-stay-hungry-stay-foolish'),
 'feynman': ('What I cannot create, I do not understand.',
             'Richard Feynman',
             'https://magazine.caltech.edu/post/biology-through-the-eyes-of-a-physicist'),
 'johnson': ("There's always something else that hasn't been found yet, so help them find it.",
             'Katherine Johnson',
             'https://time.com/4779086/katherine-goble-johnson-nasa-hidden-figures/'),
 'kay': ('The best way to predict the future is to invent it.',
         'Alan Kay',
         'https://computerhistory.org/wp-content/uploads/2019/08/core-2012.pdf'),
 'hopper': ('I think I always looked for the easiest and best, most accurate way of getting '
            'something done.',
            'Grace Hopper',
            'https://archive.computerhistory.org/resources/text/Oral_History/Hopper_Grace/102702026.05.01.pdf'),
 'turing': ('We can only see a short distance ahead, but we can see plenty there that needs to be '
            'done.',
            'Alan Turing',
            'https://turingtrust.co.uk/about-us/alan-turing/'),
 'einstein': ('The important thing is not to stop questioning.',
              'Albert Einstein',
              'https://www.pbs.org/wgbh/nova/einstein/wisd-nf.html'),
 'musk': ('I think Apollo 11 was one of the most inspiring things in all of human history.',
          'Elon Musk',
          'https://time.com/5628572/elon-musk-moon-landing/'),
 'thiel': ('But every time we create something new, we go from 0 to 1.',
           'Peter Thiel with Blake Masters',
           'https://penguinrandomhousehighereducation.com/book/?isbn=9780804139304'),
 'kennedy': ('We choose to go to the moon … not because they are easy, but because they are hard.',
             'JFK',
             'https://www.jfklibrary.org/learn/about-jfk/historic-speeches/address-at-rice-university-on-the-nations-space-effort'),
 'ride': ('Science is fun. Science is curiosity. We all have natural curiosity.',
          'Sally Ride',
          'https://assets.science.nasa.gov/content/dam/science/cds/researchers/nac/apac/2017/Harman_GS_Stars_APAC_July_2017_Tagged.pdf'),
 'arnold': ('And the way to be innovative or the way to find what you love to do is to try '
            'different things.',
            'Frances Arnold',
            'https://thereader.mitpress.mit.edu/in-conversation-with-nobel-laureate-frances-arnold/'),
 'musk_courage': ("But if something's important enough then you do it even though the risk of "
                  'failure is high.',
                  'Elon Musk',
                  'https://archive.computerhistory.org/resources/access/text/2014/03/102746849-05-01-acc.pdf'),
 'goddard': ('the dream of yesterday is the hope of today and the reality of tomorrow.',
             'Robert H. Goddard',
             'https://svs.gsfc.nasa.gov/10400'),
 'hawking': ('however difficult life may seem, there is always something you can do, and succeed '
             'at.',
             'Stephen Hawking',
             'https://www.cam.ac.uk/stories/stephen-hawking'),
 'roosevelt': ('Far better is it to dare mighty things, to win glorious triumphs, even though '
               'checkered by failure …',
               'Theodore Roosevelt',
               'https://science.nasa.gov/photojournal/mars-decoder-ring/'),
 'edison': ('Results! Why, man, I have gotten lots of results! I know several thousand things that '
            "won't work!",
            'Thomas Edison',
            'https://edison.rutgers.edu/about/news/news-the-edisonian/the-edisonian-vol-9-issue-1-winter-2012'),
 'kariko': ('always focus on what you can do, what you can change, what your next step will be.',
            'Katalin Karikó',
            'https://www.kwse.or.kr/kor/notice/news/files/pdf/Newsletter_89.pdf'),
 'goodenough': ('Think about the problem and to remember that we compete against problems, not '
                'against people.',
                'John B. Goodenough',
                'https://www.nobelprize.org/prizes/chemistry/2019/goodenough/137569-goodenough-interview-transcript/')}
ENCOURAGEMENT = {'question': ('What question would make this problem more interesting?',
              'Which assumption would be worth testing?',
              'What would you try if you were allowed to be wrong?',
              'Where does your current explanation stop making sense?'),
 'experiment': ('Try the smallest experiment that could change your mind.',
                'Make a rough version. Let it teach you what the plan cannot.',
                'What could you test before you commit to building it?',
                'A surprising result may be the most useful part of the experiment.'),
 'craft': ('What would make this easier for the next person to understand?',
           'Find one unnecessary complication. See what happens without it.',
           'Give the awkward detail a little attention; it may be telling you something.',
           'Try explaining the idea without its usual vocabulary.'),
 'perspective': ('Step back far enough to see what the problem is really asking.',
                 'Which part of this would still matter a year from now?',
                 'What might someone from another field notice here?',
                 'Is there a simpler question underneath the one you are solving?'),
 'learning': ('Write down what surprised you before it becomes familiar.',
              'Follow the part you do not quite understand yet.',
              'What did the last attempt teach you that the first plan missed?',
              'Leave a note for your future self about what you learned.'),
 'purpose': ('Who would benefit if this worked?',
             'What is worth making easier for someone else?',
             'Bring the person who will use this back into the picture.',
             'Which part of this feels worth your curiosity?'),
 'possibility': ('An unfinished idea can still be worth exploring.',
                 'What would a small, working version look like?',
                 'Give an overlooked possibility a fair test.',
                 'There may be more than one good way through this.'),
 'reflection': ('What deserves to be kept from today?',
                'A pause can make room for a different explanation.',
                'What would you like to understand better by the end of this?',
                'Notice what changed your mind. That is useful information.'),
 'elapsed': ('{hours} hours into this epoch. What has become clearer?',
             '{hours} hours have passed. Is your attention where you want it?',
             '{hours} hours in. What is worth carrying into the rest of the day?',
             '{hours} hours into your day. A moment to choose what comes next.'),
 'overrun_time': ('{extra} past the prediction. What would make a good stopping point?',
                  'An extra {extra}. Keep the time intentional.',
                  '{extra} beyond the estimate. Is this still the direction you want?',
                  '{extra} into extra time. Leave yourself a clear place to return to.')}
OVERRUN = ('You have passed the expected finish. What would make a satisfying close?',
 'The predicted window has ended. Choose what deserves your remaining attention.',
 'Past the estimate. A useful moment to decide whether to continue or wrap up.',
 'Your day ran beyond its prediction. What is worth keeping from it?')
WARNINGS = ('{remaining} to your expected finish. Choose what you want to leave complete.',
 'About {remaining} remaining. What is the most useful thing to close out?',
 '{remaining} to the predicted end. Give your next start a clear place to begin.',
 '{remaining} left in the expected window. Make room to capture what you learned.')
ONE_MINUTE = ('One minute to your expected finish. Leave a note for where to pick up.',
 'One minute remaining. What would help you return to this?',
 'Your expected finish is a minute away. Save the thought you want to keep.',
 'One minute to the prediction. Choose a good stopping point.')
STATS = {'start_consistency': ('Your last five starts span {span}, down from {previous}.',
                       'Start-time spread narrowed from {previous} to {span}.',
                       'Your recent starts are closer together: {span} versus {previous}.'),
 'duration_consistency': ('Your last five epoch lengths span {span}.',
                          'The longest and shortest of your last five epochs differ by {span}.',
                          'Five recent epoch lengths fall within a {span} range.'),
 'milestone': ('{count} included epochs completed.',
               'Your log now contains {count} completed, included epochs.',
               '{count} included epochs recorded. A moment to look back at what has changed.'),
 'month_hours': ('Over {hours} hours of included opportunity recorded this month.',
                 'This month’s included epochs total more than {hours} hours.',
                 'More than {hours} hours in this month’s included epoch log.'),
 'duration_record': ('This epoch is now longer than any other included epoch this month.',
                     'You have passed your longest included epoch this month.',
                     'A new longest included epoch for this month. A useful point to check in.'),
 'earlier_start': ('Today’s start was earlier than your previous ten included starts.',
                   'An earlier start today than any of your previous ten included epochs.',
                   'Today began ahead of your previous ten included start times.'),
 'forecast_accuracy': ('{matches} of your last five eligible finishes were within 30 minutes of the '
                       'forecast.',
                       'Forecast check: {matches} of five eligible finishes within 30 minutes.',
                       'For {matches} of your last five eligible epochs, the finish estimate was within half '
                       'an hour.'),
 'morning_pattern': ('Your last five starts this week were before 09:00.',
                     'Five recent starts this week, all before 09:00.',
                     'Before 09:00 on each of your last five starts this week.'),
 'epoch_median': ('Your last five included epochs had a median length of {duration}.',
                  'Typical epoch length across your last five included entries: {duration}.'),
 'off_time_median': ('Your last five included off-time intervals had a median length of {duration}.',
                     'Typical off-time across your last five included intervals: {duration}.'),
 'week_summary': ('{count} included epochs started this week, totaling {duration} of recorded opportunity.',
                  'This week’s completed, included epochs: {count}, with {duration} recorded.'),
 'forecast_improvement': ('Median finish-estimate error fell from {previous} to {error} across your last two '
                          'groups of five eligible epochs.',
                          'Your latest five eligible finish estimates had a median error of {error}, versus '
                          '{previous} for the previous five.')}

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
            "quotes": values.get("motivationalQuotesEnabled", True) is True,
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
        if len(epochs) >= 5:
            last = epochs[-5:]
            self.fixed.append(("epoch_median", fact_key("epoch_median", last),
                               {"duration": length(median(s["durationMs"] for s in last))}))
        off_times = [s for s in state["history"] if s["kind"] == "off"
                     and s["durationMs"] >= 0 and not s.get("excludedFromLearning", False)]
        if len(off_times) >= 5:
            last = off_times[-5:]
            self.fixed.append(("off_time_median", fact_key("off_time_median", last),
                               {"duration": length(median(s["durationMs"] for s in last))}))
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
        eligible = [s for s in epochs if type(s.get("expectedDurationMs")) in (int, float)
                    and math.isfinite(s["expectedDurationMs"]) and s["expectedDurationMs"] >= 1000]
        if len(eligible) >= 10:
            last = eligible[-10:]
            errors = [abs(s["durationMs"] - s["expectedDurationMs"]) for s in last]
            before, after = median(errors[:5]), median(errors[5:])
            if before >= MINUTE and after <= before * 0.75:
                self.fixed.append(("forecast_improvement", fact_key("forecast_improvement", last),
                                   {"previous": length(before), "error": length(after)}))
        week = current.isocalendar()[:2]
        completed_week = [s for s, d in starts if d.isocalendar()[:2] == week]
        if len(completed_week) >= 3:
            self.fixed.append(("week_summary", fact_key("week_summary", completed_week),
                               {"count": len(completed_week),
                                "duration": length(sum(s["durationMs"] for s in completed_week))}))
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
        meanings = [k for k in meanings if k not in book["recentKinds"][-4:]] or ["question"]
        # Quotes are distinct messages, not alternate wording of a prompt.
        # Never recycle a quote while it remains in the recent-message window.
        quotes = [key for key in QUOTES
                  if self.config["quotes"] and "quote:" + key not in book["recentKinds"][-4:]
                  and "quote:" + key + ":0" not in book["recentMessages"]]
        if candidates and self.rng.random() < 0.65:
            kind, fact, fields = self.rng.choice(candidates)
            pool = STATS[kind]
        elif quotes and self.rng.random() < 0.65:
            key = self.rng.choice(quotes)
            quote, author, _ = QUOTES[key]
            kind = "quote:" + key
            return self.phrase(kind, kind, {}, (f'“{quote}” — {author}',), preview)
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

    def tick(self, age, now, suppress_focus=False):
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
                if not suppress_focus and not gap and message is None and not cooling and not upcoming:
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
