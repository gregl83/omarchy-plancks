import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import insights as i
import plancks as p

HOUR, MINUTE = i.HOUR, i.MINUTE


class InsightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = p.blank_state()
        self.utc = int(datetime(2026, 10, 9, 7).astimezone().timestamp() * 1000)
        self.state.update(generation='generation', sequence=1, phase='active', epochId='epoch',
                          anchor={'utcMs': self.utc, 'bootMs': 0, 'bootId': 'test'}, predictionMs=14 * HOUR)
        self.engine = i.Insights(self.temp.name, random.Random(17))

    def start(self, **settings):
        self.engine.configure(settings)
        self.engine.sync(self.state, 0)
        return self.engine

    def due(self, age, engine=None):
        engine = engine or self.engine
        engine.last_age = age - 1000
        return engine.tick(age, {'utcMs': self.utc + age})

    def test_default_and_off_time_are_silent_without_io(self):
        self.engine.sync(self.state, 0)
        with patch.object(self.engine, 'read', side_effect=AssertionError('read')), \
             patch.object(self.engine, 'save', side_effect=AssertionError('write')):
            self.assertIsNone(self.engine.tick(HOUR, {'utcMs': self.utc + HOUR}))
            self.engine.configure({'insightsEnabled': True, 'finishNotificationsEnabled': True})
            self.state['phase'] = 'off'
            self.engine.sync(self.state, HOUR)
            self.assertIsNone(self.engine.tick(30 * HOUR, {'utcMs': self.utc + 30 * HOUR}))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_independent_finish_warnings_and_one_overrun(self):
        self.start(insightsEnabled=True, finishNotificationsEnabled=True)
        for seconds in (1800, 60):
            age = self.state['predictionMs'] - seconds * 1000
            self.engine.book['next'] = age + 10 * HOUR
            self.engine.save()
            notice = self.due(age)
            self.assertEqual(notice['kind'], f'warning:{seconds}')
            self.assertIsNone(self.due(age + 1000))
        age = 14 * HOUR + 90_000
        self.assertEqual(self.due(age)['kind'], 'overrun')
        self.assertIsNone(self.due(age + 1000))
        fresh = i.Insights(self.temp.name)
        fresh.configure({'finishNotificationsEnabled': True})
        fresh.sync(self.state, age + 1000)
        self.assertIsNone(self.due(age + 2000, fresh))

    def test_restart_preserves_schedule_and_two_helpers_claim_once(self):
        self.start(insightsEnabled=True)
        deadline = self.engine.book['next']
        fresh = i.Insights(self.temp.name, random.Random(18))
        fresh.configure({'insightsEnabled': True})
        fresh.sync(self.state, MINUTE)
        self.assertEqual(fresh.book['next'], deadline)
        self.assertIsNotNone(self.due(deadline))
        self.assertIsNone(self.due(deadline, fresh))
        self.assertTrue(2 * HOUR <= self.engine.book['next'] - deadline <= 3 * HOUR)

    def test_suspend_skips_missed_alerts_and_insights(self):
        self.start(insightsEnabled=True, finishNotificationsEnabled=True)
        age = 15 * HOUR
        self.assertIsNone(self.engine.tick(age, {'utcMs': self.utc + age}))
        self.assertEqual(set(self.engine.book['delivered']), {'warning:1800', 'warning:60', 'overrun'})
        self.assertGreater(self.engine.book['next'], age)
        self.assertIsNone(self.due(age + 1000))

    def test_cadences_and_no_tick_io_or_aggregation_before_deadline(self):
        for frequency, (low, high) in i.CADENCE.items():
            self.start(insightsEnabled=True, insightFrequency=frequency)
            self.assertTrue(90 * MINUTE <= self.engine.book['next'] <= 105 * MINUTE)
            self.assertTrue(low <= self.engine.interval() <= high)
        with patch.object(self.engine, 'read', side_effect=AssertionError('read')), \
             patch.object(self.engine, 'save', side_effect=AssertionError('write')), \
             patch.object(self.engine.stats, 'update', side_effect=AssertionError('history scan')):
            for age in range(1000, 90 * MINUTE, 1000):
                self.assertIsNone(self.engine.tick(age, {'utcMs': self.utc + age}))
        self.assertEqual(self.engine.stats.builds, 1)

    def test_preview_does_not_schedule_or_change_history(self):
        before = copy.deepcopy(self.state)
        preview = self.engine.preview(self.state, HOUR)
        self.assertTrue(preview['preview'])
        self.assertTrue(preview['message'])
        self.assertEqual(self.state, before)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_previews_vary_without_consuming_scheduled_facts(self):
        self.start(insightsEnabled=True)
        saved_book = copy.deepcopy(self.engine.book)
        saved_disk = self.engine.path.read_bytes()
        recent_kinds, recent_messages = [], []
        with patch.object(self.engine.stats, 'candidates', return_value=[
                ('month_hours', 'month:2026-10:20', {'hours': 20})]):
            samples = [self.engine.preview(self.state, HOUR) for _ in range(30)]
        for message in samples:
            self.assertNotIn(message['kind'], recent_kinds[-4:])
            self.assertNotIn(message['messageId'], recent_messages[-30:])
            recent_kinds.append(message['kind'])
            recent_messages.append(message['messageId'])
        self.assertEqual(sum(m['kind'] == 'month_hours' for m in samples), 1)
        self.assertEqual(self.engine.book, saved_book)
        self.assertEqual(self.engine.path.read_bytes(), saved_disk)

    def test_nearby_finish_warning_takes_priority(self):
        self.start(insightsEnabled=True, finishNotificationsEnabled=True)
        age = 14 * HOUR - 1800 * 1000
        self.engine.book['next'] = age
        self.engine.save()
        self.assertEqual(self.due(age)['kind'], 'warning:1800')
        self.assertGreater(self.engine.book['next'], age)

    def test_invalid_settings_and_corrupt_progress(self):
        config = i.normalize_settings({'insightsEnabled': 'true', 'insightFrequency': 'no',
                                       'finishWarningSeconds': [True, -1]})
        self.assertFalse(config['enabled'])
        self.assertEqual(config['warnings'], [1800, 60])
        self.engine.path.write_text('{broken')
        self.start(insightsEnabled=True)
        self.assertEqual(json.loads(self.engine.path.read_text())['epoch'], 'epoch')

    def test_stats_filter_excluded_and_invalid_and_cache_revision(self):
        history = []
        for n in range(10):
            start = self.utc - (10 - n) * 24 * HOUR
            history.append({'eventId': str(n), 'kind': 'epoch', 'start': {'utcMs': start},
                            'durationMs': 12 * HOUR, 'expectedDurationMs': 12 * HOUR + MINUTE})
        self.state['history'] = history + [dict(history[0], eventId='excluded', durationMs=100 * HOUR,
                                                excludedFromLearning=True),
                                          dict(history[0], eventId='invalid', durationMs=-1)]
        stats = i.Statistics()
        stats.update(self.state)
        kinds = {kind: values for kind, _, values in stats.fixed}
        self.assertEqual(kinds['milestone']['count'], 10)
        self.assertEqual(kinds['forecast_accuracy']['matches'], 5)
        self.assertEqual(stats.month_max, 12 * HOUR)
        self.assertIn('duration_record', [c[0] for c in stats.candidates(self.state, 13 * HOUR)])
        stats.update(self.state)
        self.assertEqual(stats.builds, 1)
        history[-1]['excludedFromLearning'] = True
        self.state['sequence'] += 1
        stats.update(self.state)
        self.assertNotIn('milestone', [c[0] for c in stats.fixed])
        self.assertEqual(stats.builds, 2)

    def test_forecast_is_saved_with_completed_epoch_and_reset_clears_progress(self):
        store = p.Store(self.temp.name)
        with patch.object(p, 'clock', return_value=self.state['anchor']):
            state, _ = store.transition('start', 'start', 0, HOUR)
        finish = dict(self.state['anchor'], utcMs=self.utc + HOUR, bootMs=HOUR)
        with patch.object(p, 'clock', return_value=finish):
            state, _ = store.transition('end', 'end', state['sequence'], HOUR)
        self.assertEqual(state['history'][0]['expectedDurationMs'], HOUR)
        self.start(insightsEnabled=True)
        store.reset('reset', state['generation'], state['sequence'])
        self.assertFalse(self.engine.path.exists())

    def test_meaning_and_wording_variations_avoid_recent_repeats(self):
        self.start(insightsEnabled=True)
        recent = []
        for n in range(20):
            message = self.engine.choose(HOUR)
            self.assertNotIn(message['kind'], self.engine.book['recentKinds'][-4:])
            self.assertNotIn(message['messageId'], recent[-30:])
            self.engine.book['recentKinds'].append(message['kind'])
            self.engine.book['recentMessages'].append(message['messageId'])
            recent.append(message['messageId'])


if __name__ == '__main__':
    unittest.main()
