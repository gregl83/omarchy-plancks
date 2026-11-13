"""Corrections remain reversible and durable across adjacent boundaries."""
import copy
import tempfile
import unittest
from unittest.mock import patch

import plancks as p
from test_plancks import at, HOUR


class HistoryEditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = p.Store(self.temp.name)
        for i, (action, hour) in enumerate([('start', 0), ('end', 8), ('start', 24), ('end', 32)]):
            self.store.transition(action, 'event-' + str(i), i, now=at(hour))

    def edit(self, sample='event-2', start=9, end=23, request='correction', sequence=None):
        state = self.store.load()
        with patch.object(p, 'clock', return_value=at(40)):
            return self.store.edit_times(sample, at(start)['utcMs'], at(end)['utcMs'], request,
                                         state['sequence'] if sequence is None else sequence,
                                         state['generation'])[0]

    def test_shared_boundaries_predictions_replay_and_restore(self):
        state = self.edit()
        rows = state['history']
        self.assertEqual([r['durationMs'] / HOUR for r in rows], [9, 14, 9])
        self.assertEqual(rows[0]['end'], rows[1]['start'])
        self.assertEqual(rows[1]['end'], rows[2]['start'])
        self.assertTrue(all(r['edited'] for r in rows))
        self.assertEqual(state['predictionMs'], 14 * HOUR)
        replay = p.Store(self.temp.name).recover()
        self.assertEqual(state['history'], replay['history'])
        restored = self.edit(start=8, end=24, request='restore')
        self.assertEqual([r['durationMs'] / HOUR for r in restored['history']], [8, 16, 8])
        self.assertTrue(all(not r['edited'] for r in restored['history']))
        self.assertEqual(restored['history'][1]['timeBasis'], 'boottime')

    def test_latest_boundary_updates_open_interval(self):
        state = self.edit(sample='event-3', start=24, end=31)
        self.assertEqual(state['anchor']['utcMs'], at(31)['utcMs'])
        self.assertEqual(p.elapsed(state['anchor'], at(40))[0], 9 * HOUR)
        self.assertEqual(state['lastEnd'], state['anchor'])

    def test_inclusion_preserved(self):
        state = self.store.load()
        self.store.set_inclusion('event-2', True, 'exclude', state['sequence'])
        state = self.edit()
        self.assertTrue(state['history'][1]['excludedFromLearning'])
        self.assertEqual(state['gapSamples'], [])

    def test_invalid_inputs_leave_journal_unchanged(self):
        before = copy.deepcopy(self.store.recover())
        for start, end in [(0, 24), (9, 32), (25, 24), (8, 41), (8, 8)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.edit(start=start, end=end)
            self.assertEqual(self.store.load(), before)
        for value in [True, 1.5, 'bad', None]:
            with self.subTest(value=value), patch.object(p, 'clock', return_value=at(40)), self.assertRaises(ValueError):
                self.store.edit_times('event-2', value, at(23)['utcMs'], 'invalid', before['sequence'])

    def test_retries_conflicts_and_stale_edits(self):
        first = self.edit()
        self.assertEqual(self.edit(sequence=4)['sequence'], first['sequence'])
        with self.assertRaises(ValueError):
            self.edit(start=10)
        with self.assertRaises(ValueError):
            self.edit(request='stale', sequence=4)
        with self.assertRaises(ValueError):
            self.store.edit_times('event-2', at(9)['utcMs'], at(23)['utcMs'], 'reset', first['sequence'], 'wrong')

    def test_correction_repairs_clock_error(self):
        with tempfile.TemporaryDirectory() as directory:
            store = p.Store(directory)
            store.transition('start', 'a', 0, now=at(10))
            store.transition('end', 'b', 1, now=at(11, 'reboot', 9))
            with patch.object(p, 'clock', return_value=at(20)):
                state, _ = store.edit_times('b', at(8)['utcMs'], at(9)['utcMs'], 'repair', 2)
            self.assertEqual(state['history'][0]['durationMs'], HOUR)
            self.assertEqual(state['workSamples'][0]['eventId'], 'b')
