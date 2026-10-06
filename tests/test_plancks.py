import json
import os
from pathlib import Path
import tempfile
import subprocess
import select
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plancks as p

HOUR = 3600000


def at(hours, boot='test', utc_hours=None):
    return {'bootId': boot, 'bootMs': int(hours * HOUR),
            'utcMs': 1700000000000 + int((hours if utc_hours is None else utc_hours) * HOUR)}


class ModelTests(unittest.TestCase):
    def test_trimmed_recent_five(self):
        samples = [{'durationMs': h * HOUR} for h in [100, 12, 16, 14, 18, 15]]
        self.assertEqual(p.estimate(samples), 15 * HOUR)
        self.assertEqual(p.estimate([{'durationMs': HOUR}] * 5), HOUR)
        self.assertIsNone(p.estimate([]))
        self.assertEqual(p.estimate([], HOUR), HOUR)
        for values, expected in [([1], 1), ([1, 3], 2), ([1, 4, 9], 4), ([1, 4, 6, 9], 5)]:
            self.assertEqual(p.estimate([{'durationMs': h * HOUR} for h in values]), expected * HOUR)
        self.assertEqual(p.estimate([{'durationMs': 0}]), 1000)
        self.assertEqual(p.estimate([{'durationMs': 1500}]), 2000)

    def test_clock_basis(self):
        self.assertEqual(p.elapsed(at(7), at(23, utc_hours=25)), (16 * HOUR, 'boottime'))
        self.assertEqual(p.elapsed(at(7), at(1, 'reboot', 23)), (16 * HOUR, 'utc-fallback'))
        self.assertEqual(p.duration(100 * HOUR), '100:00:00')

    def test_phase_and_signs(self):
        for phase, indicator in [('active', '●'), ('off', '○')]:
            state = p.blank_state()
            state.update(phase=phase, anchor=at(0), predictionMs=HOUR)
            for now, expected in [(0, '−01:00:00'), (1, '00:00:00'), (2, '+01:00:00')]:
                result = p.view(state, at(now))
                self.assertEqual(result['timer'], expected)
                self.assertEqual(result['indicator'], indicator)
            state['predictionMs'] = None
            result = p.view(state, at(1))
            self.assertEqual(result['timer'], '+01:00:00')
            self.assertIn('elapsed · learning your rhythm', result['status'])

    def test_display_ticks_do_not_read_files_copy_state_or_reestimate(self):
        state = p.blank_state()
        state.update(phase='active', anchor=at(7), predictionMs=16 * HOUR)
        display = p.Display(state, now=at(7))
        with patch.object(p, 'estimate', side_effect=AssertionError('recomputed prediction')), \
             patch.object(Path, 'open', side_effect=AssertionError('filesystem read')), \
             patch.object(p.copy, 'deepcopy', side_effect=AssertionError('copied history')):
            for hour in [8, 12, 24]:
                result = display.update(at(hour))
            self.assertEqual(result['timer'], '+01:00:00')
            self.assertEqual(result['predictedEndUtcMs'], at(23)['utcMs'])
            corrected = display.update(at(25, utc_hours=26))
            self.assertEqual(corrected['timer'], '+02:00:00')
            self.assertEqual(corrected['predictedEndUtcMs'], at(24)['utcMs'])



class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = p.Store(self.temp.name)
        self.n = 0

    def transition(self, action, hours, **kwargs):
        self.n += 1
        return self.store.transition(action, f'event-{self.n}', self.store.load()['sequence'], now=at(hours), **kwargs)[0]

    def include(self, sample_id, excluded, request_id='edit', **kwargs):
        state = self.store.load()
        return self.store.set_inclusion(sample_id, excluded, request_id, state['sequence'],
                                        state['generation'], **kwargs)[0]

    def test_history_trends_are_bounded_chronological_and_independent_of_page(self):
        self.assertEqual(self.store.history_page()['trends'], {'epoch': [], 'off': []})
        for i in range(24):
            self.transition('start' if i % 2 == 0 else 'end', i, skip_learning=i == 23)
        first = self.store.history_page()
        last = self.store.history_page(4)
        self.assertEqual(first['trends'], last['trends'])
        epochs = first['trends']['epoch']
        gaps = first['trends']['off']
        self.assertEqual(len(epochs), 10)
        self.assertEqual(len(gaps), 10)
        self.assertEqual(epochs[0]['eventId'], 'event-6')
        self.assertEqual(epochs[-1]['eventId'], 'event-24')
        self.assertTrue(epochs[-1]['excludedFromLearning'])
        self.assertEqual([p['endUtcMs'] for p in gaps], sorted(p['endUtcMs'] for p in gaps))
        self.include('event-24', False)
        self.assertFalse(self.store.history_page()['trends']['epoch'][-1]['excludedFromLearning'])

    def test_history_pagination_includes_skipped_and_replays_rotated_records(self):
        for i in range(14):
            self.transition('start' if i % 2 == 0 else 'end', i,
                            skip_learning=i == 3, rotate_bytes=1)
        first = self.store.history_page()
        self.assertEqual((first['total'], first['pages'], len(first['rows'])), (13, 3, 5))
        self.assertEqual(first['rows'][0]['eventId'], 'event-14')
        second = self.store.history_page(1)
        self.assertEqual(len(second['rows']), 5)
        third = self.store.history_page(2)
        self.assertEqual(len(third['rows']), 3)
        self.assertTrue(third['rows'][0]['excludedFromLearning'])
        self.assertEqual(self.store.history_page(100)['page'], 2)
        recovered = p.Store(self.temp.name)
        self.assertEqual(recovered.history_page(), first)
        with self.assertRaises(ValueError):
            self.store.history_page(-1)

    def test_exclusion_backfills_older_sample_and_updates_active_prediction(self):
        hour = 0
        for length in [1, 2, 4, 6, 8, 10]:
            self.transition('start', hour)
            hour += length
            self.transition('end', hour)
            hour += 1
        active = self.transition('start', hour)
        anchor = active['anchor']
        edited = self.include('event-12', True)
        self.assertEqual([s['durationMs'] // HOUR for s in edited['workSamples']], [1, 2, 4, 6, 8])
        self.assertEqual(edited['predictionMs'], 4 * HOUR)
        self.assertEqual(edited['anchor'], anchor)
        self.assertEqual(edited['phase'], 'active')
        self.assertEqual(p.view(edited, at(hour + 1))['timer'], '−03:00:00')
        self.assertEqual(p.view(edited, at(hour + 1))['predictedEndUtcMs'], at(hour + 4)['utcMs'])
        self.assertEqual(p.Store(self.temp.name).recover(), edited)
        restored = self.include('event-12', False, 'restore')
        self.assertEqual(restored['predictionMs'], active['predictionMs'])

    def test_old_exclusions_and_other_interval_type_preserve_frozen_prediction(self):
        for i in range(14):
            self.transition('start' if i % 2 == 0 else 'end', i)
        active = self.transition('start', 14)
        older = self.include('event-2', True)
        self.assertEqual(older['predictionMs'], active['predictionMs'])
        gap = self.include('event-15', True, 'gap-edit')
        self.assertEqual(gap['predictionMs'], active['predictionMs'])
        self.assertEqual(gap['workSamples'], older['workSamples'])
        self.assertEqual(gap['anchor'], active['anchor'])

    def test_removing_all_work_samples_uses_fallback_or_learning(self):
        self.transition('start', 0)
        self.transition('end', 4, skip_learning=True)
        self.transition('start', 5)
        included = self.include('event-2', False)
        self.assertEqual(included['predictionMs'], 4 * HOUR)
        fallback = self.include('event-2', True, 'fallback', initial_ms=8 * HOUR)
        self.assertEqual(fallback['predictionMs'], 8 * HOUR)
        self.include('event-2', False, 'restore')
        learning = self.include('event-2', True, 'learning')
        self.assertIsNone(learning['predictionMs'])
        self.assertEqual(p.view(learning, at(6))['timer'], '+01:00:00')

    def test_off_time_exclusion_updates_current_off_time(self):
        self.transition('start', 0)
        self.transition('end', 4)
        self.transition('start', 6)
        off = self.transition('end', 10)
        self.assertEqual(off['predictionMs'], 2 * HOUR)
        edited = self.include('event-3', True)
        self.assertIsNone(edited['predictionMs'])
        self.assertEqual(edited['anchor'], off['anchor'])
        restored = self.include('event-3', False, 'restore')
        self.assertEqual(p.view(restored, at(11))['predictedStartUtcMs'], at(12)['utcMs'])

    def test_history_edit_retries_stale_revisions_and_reset_generation(self):
        self.transition('start', 0)
        before = self.transition('end', 4)
        edited = self.include('event-2', True)
        duplicate, _ = self.store.set_inclusion('event-2', True, 'edit', before['sequence'])
        self.assertEqual(duplicate, edited)
        with self.assertRaisesRegex(ValueError, 'another action'):
            self.store.set_inclusion('event-2', False, 'edit', edited['sequence'])
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.store.set_inclusion('event-2', False, 'stale', before['sequence'])
        self.store.reset('reset-history', '', edited['sequence'])
        self.assertEqual(self.store.history_page()['total'], 0)
        with self.assertRaisesRegex(ValueError, 'reset'):
            self.store.set_inclusion('event-2', True, 'edit', edited['sequence'])

    def test_history_edit_retry_after_uncertain_append_is_durable_and_idempotent(self):
        self.transition('start', 0)
        before = self.transition('end', 4)
        with patch.object(p.os, 'fsync', side_effect=OSError('uncertain append')):
            with self.assertRaises(OSError):
                self.include('event-2', True)
        recovered = p.Store(self.temp.name)
        with patch.object(p.os, 'fsync', wraps=p.os.fsync) as synced:
            state, _ = recovered.set_inclusion('event-2', True, 'edit', before['sequence'])
            self.assertTrue(synced.called)
        self.assertEqual(state['sequence'], before['sequence'] + 1)
        self.assertTrue(recovered.history_page()['rows'][0]['excludedFromLearning'])
        self.assertEqual(len(state['history']), 1)

    def test_invalid_clock_interval_cannot_be_reincluded(self):
        self.transition('start', 5)
        self.transition('end', 4)
        row = self.store.history_page()['rows'][0]
        self.assertEqual(self.store.history_page()['trends'], {'epoch': [], 'off': []})
        self.assertLess(row['durationMs'], 0)
        self.assertFalse(row['recent'])
        with self.assertRaisesRegex(ValueError, 'invalid history interval'):
            self.include('event-2', False)

    def test_daily_window_and_independent_gaps(self):
        first = self.transition('start', 7)
        self.assertIsNone(first['predictionMs'])
        end = self.transition('end', 23)
        self.assertEqual(end['workSamples'][0]['durationMs'], 16 * HOUR)
        self.assertIsNone(end['predictionMs'])
        second = self.transition('start', 31)
        self.assertEqual(second['predictionMs'], 16 * HOUR)
        self.assertEqual(second['gapSamples'][0]['durationMs'], 8 * HOUR)
        result = p.view(second, at(32))
        self.assertEqual(result['predictedEndUtcMs'], at(47)['utcMs'])
        self.assertEqual(result['predictedStartUtcMs'], at(55)['utcMs'])
        end2 = self.transition('end', 49)  # two hours of overrun are part of the epoch
        self.assertEqual(end2['workSamples'][-1]['durationMs'], 18 * HOUR)
        self.assertEqual(p.view(end2, at(50))['predictedStartUtcMs'], at(57)['utcMs'])

    def test_skip_preserves_history_and_resumes_learning_after_recovery(self):
        self.transition('start', 7)
        self.transition('end', 23)
        self.transition('start', 31)
        before = self.transition('end', 47)
        skipped_gap = self.transition('start', 103, skip_learning=True)
        self.assertEqual(skipped_gap['gapSamples'], before['gapSamples'])
        self.assertEqual(skipped_gap['predictionMs'], 16 * HOUR)
        skipped_epoch = self.transition('end', 150, skip_learning=True)
        self.assertEqual(skipped_epoch['workSamples'], before['workSamples'])
        self.assertEqual(skipped_epoch['predictionMs'], 8 * HOUR)
        records = [json.loads(line) for line in next(self.store.events.glob('*.jsonl')).read_text().splitlines()]
        self.assertNotIn('excludedFromLearning', records[1]['completedSample'])
        for record, hours in [(records[-2], 56), (records[-1], 47)]:
            self.assertTrue(record['completedSample']['excludedFromLearning'])
            self.assertEqual(record['completedSample']['durationMs'], hours * HOUR)
            self.assertEqual(record['completedSample']['end'], record['clock'])
            self.assertEqual(record['schemaVersion'], 1)
        (self.store.root / 'state.json').unlink()
        self.store = p.Store(self.temp.name)
        self.assertEqual(self.store.recover()['workSamples'], before['workSamples'])
        self.assertEqual(self.store.load()['gapSamples'], before['gapSamples'])
        start = self.transition('start', 158)
        self.assertEqual(len(start['gapSamples']), 2)
        end = self.transition('end', 174)
        self.assertEqual(len(end['workSamples']), 3)
        self.assertEqual(end['predictionMs'], 8 * HOUR)

    def test_skip_retry_and_stale_commands(self):
        self.transition('start', 7)
        self.transition('end', 23, skip_learning=True)
        store = p.Store(self.temp.name)
        retry, _ = store.transition('end', 'event-2', 1, now=at(24), skip_learning=True)
        self.assertEqual(retry['sequence'], 2)
        self.assertEqual(retry['workSamples'], [])
        with self.assertRaisesRegex(ValueError, 'another action'):
            store.transition('end', 'event-2', 1)
        with self.assertRaisesRegex(ValueError, 'another screen'):
            store.transition('start', 'stale', 1, skip_learning=True)
        with self.assertRaisesRegex(ValueError, 'boolean'):
            store.transition('start', 'invalid', 2, skip_learning='true')
        self.assertEqual(store.load()['sequence'], 2)

    def test_skip_without_history_and_invalid_replayed_flag(self):
        first = self.transition('start', 7, skip_learning=True, initial_ms=HOUR)
        self.assertEqual(first['predictionMs'], HOUR)
        self.transition('end', 23, skip_learning=True)
        self.assertEqual(self.store.load()['workSamples'], [])
        segment = next(self.store.events.glob('*.jsonl'))
        records = [json.loads(line) for line in segment.read_text().splitlines()]
        records[-1]['completedSample']['excludedFromLearning'] = 'true'
        segment.write_text(''.join(json.dumps(record) + '\n' for record in records))
        with self.assertRaisesRegex(ValueError, 'exclusion flag'):
            p.Store(self.temp.name).recover()

    def test_server_skip_protocol(self):
        requests = [
            {'action': 'start', 'sequence': 0, 'requestId': 'start'},
            {'action': 'end', 'sequence': 1, 'requestId': 'end', 'skipLearning': True},
            {'action': 'end', 'sequence': 1, 'requestId': 'end', 'skipLearning': True},
            {'action': 'start', 'sequence': 2, 'requestId': 'next', 'skipLearning': True},
        ]
        result = subprocess.run([sys.executable, str(Path(p.__file__)), 'serve', '--state-dir', self.temp.name],
                                input=''.join(json.dumps(r) + '\n' for r in requests),
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(all(reply['ok'] for reply in replies))
        self.assertEqual(replies[-1]['view']['sequence'], 3)
        self.assertEqual(replies[-1]['view']['workSampleCount'], 0)
        self.assertEqual(replies[-1]['view']['gapSampleCount'], 0)

    def test_first_off_time_counts_up_until_a_prediction_is_learned(self):
        initial = p.Display(self.store.load(), now=at(0))
        self.assertEqual(initial.values['timer'], '--:--:--')
        self.assertFalse(initial.ticking(False))
        self.transition('start', 7)
        end = self.transition('end', 23)
        display = p.Display(end, now=at(23))
        self.assertEqual(display.values['timer'], '+00:00:00')
        self.assertTrue(display.ticking(False))
        self.assertEqual(display.update(at(24))['timer'], '+01:00:00')
        self.assertEqual(display.values['status'], 'Off-time · Off-time elapsed · learning your rhythm')
        self.assertIsNone(display.values['predictedStartUtcMs'])
        recovered = p.Display(p.Store(self.temp.name).recover(), now=at(25))
        self.assertEqual(recovered.values['timer'], '+02:00:00')
        self.transition('start', 31)
        end = self.transition('end', 47)
        self.assertEqual(p.view(end, at(47))['timer'], '−08:00:00')
        reset = self.store.reset('reset', '', 4)
        self.assertEqual(p.view(reset, at(48))['timer'], '--:--:--')

    def test_rotation_and_snapshot_rebuild(self):
        first = self.transition('start', 7, rotate_bytes=1)
        segment = next(self.store.events.glob('*.jsonl'))
        original = segment.read_bytes()
        self.transition('end', 23, rotate_bytes=1)
        self.assertEqual(segment.read_bytes(), original)
        self.assertEqual(len(list(self.store.events.glob('*.jsonl'))), 2)
        (self.store.root / 'state.json').write_text('broken snapshot')
        recovered = p.Store(self.temp.name).recover()
        self.assertEqual(recovered['phase'], 'off')
        self.assertEqual(recovered['workSamples'][0]['durationMs'], 16 * HOUR)
        self.assertEqual(recovered, json.loads((self.store.root / 'state.json').read_text()))

    def test_commit_before_snapshot_failure_and_retry(self):
        with patch.object(self.store, 'snapshot', side_effect=OSError('disk full')):
            state, warning = self.store.transition('start', 'stable-id', 0, now=at(7))
        self.assertIn('saved in the journal', warning)
        self.assertEqual(state['phase'], 'active')
        recovered = p.Store(self.temp.name)
        state = recovered.recover()
        duplicate, _ = recovered.transition('start', 'stable-id', 0, now=at(8))
        self.assertEqual(duplicate['sequence'], 1)
        self.assertEqual(duplicate['anchor'], at(7))
        with self.assertRaises(ValueError):
            recovered.transition('end', 'stable-id', 1, now=at(8))

    def test_retry_after_sync_failure_requires_durability(self):
        for failure in ('file', 'directory'):
            for restart in (False, True):
                with self.subTest(failure=failure, restart=restart), tempfile.TemporaryDirectory() as directory:
                    store = p.Store(directory)
                    target, name = (p.os, 'fsync') if failure == 'file' else (p, 'sync_dir')
                    with patch.object(target, name, side_effect=OSError('sync failed')):
                        with self.assertRaises(OSError):
                            store.transition('start', 'retry-id', 0, now=at(7))
                    segment = next(store.events.glob('*.jsonl'))
                    original = segment.read_bytes()
                    if restart:
                        store = p.Store(directory)
                    with patch.object(target, name, side_effect=OSError('still failing')):
                        with self.assertRaises(OSError):
                            store.transition('start', 'retry-id', 0, now=at(8))
                    with patch.object(p.os, 'fsync', wraps=p.os.fsync) as sync:
                        state, warning = store.transition('start', 'retry-id', 0, now=at(9))
                    self.assertGreaterEqual(sync.call_count, 4)  # journal, directory, snapshot, directory
                    self.assertIsNone(warning)
                    self.assertEqual(state['sequence'], 1)
                    self.assertEqual(state['anchor'], at(7))
                    self.assertEqual(segment.read_bytes(), original)
                    self.assertEqual(json.loads((store.root / 'state.json').read_text()), state)

    def test_retry_old_rotated_event_preserves_newer_history(self):
        self.store.transition('start', 'old', 0, now=at(7), rotate_bytes=1)
        current, _ = self.store.transition('end', 'new', 1, now=at(23), rotate_bytes=1)
        segments = {path: path.read_bytes() for path in self.store.events.glob('*.jsonl')}
        synced = []
        real_sync = p.os.fsync
        def record_sync(fd):
            synced.append(os.readlink(f'/proc/self/fd/{fd}'))
            real_sync(fd)
        with patch.object(p.os, 'fsync', side_effect=record_sync):
            state, warning = p.Store(self.temp.name).transition('start', 'old', 0)
        self.assertIn(str(self.store.events / 'events-00000001.jsonl'), synced)
        self.assertEqual(state, current)
        self.assertIsNone(warning)
        self.assertEqual({path: path.read_bytes() for path in segments}, segments)

    def test_torn_tail_preserved_and_rotated(self):
        self.transition('start', 7)
        segment = next(self.store.events.glob('*.jsonl'))
        with segment.open('ab') as stream:
            stream.write(b'{"incomplete":')
        original = segment.read_bytes()
        self.transition('end', 23)
        self.assertEqual(segment.read_bytes(), original)
        self.assertEqual(len(list(self.store.events.glob('*.jsonl'))), 2)
        self.assertEqual(p.Store(self.temp.name).recover()['sequence'], 2)

    def test_corrupt_complete_record_and_missing_segment_block(self):
        self.transition('start', 7)
        segment = next(self.store.events.glob('*.jsonl'))
        with segment.open('ab') as stream:
            stream.write(b'{bad json}\n')
        with self.assertRaisesRegex(ValueError, 'Invalid record'):
            self.store.recover()
        segment.rename(segment.with_name('events-00000002.jsonl'))
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.store.recover()

    def test_missing_final_segment_does_not_reset_history(self):
        self.transition('start', 7, rotate_bytes=1)
        self.transition('end', 23, rotate_bytes=1)
        saved = (self.store.root / 'state.json').read_bytes()
        (self.store.events / 'events-00000002.jsonl').unlink()
        with self.assertRaisesRegex(ValueError, 'restore missing'):
            p.Store(self.temp.name).recover()
        self.assertEqual((self.store.root / 'state.json').read_bytes(), saved)

    def test_stale_concurrent_command_rejected(self):
        other = p.Store(self.temp.name)
        self.transition('start', 7)
        with self.assertRaisesRegex(ValueError, 'another screen'):
            other.transition('start', 'other-screen', 0, now=at(7))
        self.assertEqual(other.recover()['sequence'], 1)

    def test_failed_append_leaves_phase_unchanged(self):
        with patch.object(self.store, 'append', side_effect=OSError('read only')):
            with self.assertRaises(OSError):
                self.transition('start', 7)
        self.assertEqual(self.store.recover()['phase'], 'off')

    def test_no_writes_on_ticks_and_frozen_prediction(self):
        state = self.transition('start', 7, initial_ms=16 * HOUR)
        snapshot = self.store.root / 'state.json'
        original = snapshot.stat().st_mtime_ns
        for hour in [8, 12, 26]:
            p.view(self.store.load(), at(hour), initial_ms=2 * HOUR)
        self.assertEqual(snapshot.stat().st_mtime_ns, original)
        self.assertEqual(self.store.load()['predictionMs'], 16 * HOUR)
        self.assertEqual(p.Store(self.temp.name).recover()['deadlineUtcMs'], at(23)['utcMs'])

    def test_invalid_cross_boot_duration_is_excluded(self):
        self.transition('start', 7)
        state, _ = self.store.transition('end', 'end', 1, now=at(1, 'other', 6))
        self.assertEqual(state['workSamples'], [])
        self.assertTrue(state['warnings'])

    def test_parallel_writers_commit_once(self):
        def start(n):
            try:
                return p.Store(self.temp.name).transition('start', f'parallel-{n}', 0, now=at(7))[0]['sequence']
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(start, range(4)))
        self.assertEqual(results.count(1), 1)
        self.assertEqual(self.store.recover()['sequence'], 1)

    def test_server_protocol_and_duplicate_retry(self):
        requests = [
            {'action': 'configure', 'initialSeconds': 3600},
            {'action': 'start', 'sequence': 0, 'requestId': 'start-id'},
            {'action': 'start', 'sequence': 0, 'requestId': 'start-id'},
            {'action': 'end', 'sequence': 1, 'requestId': 'end-id'},
            {'action': 'start', 'sequence': 0, 'requestId': 'stale-id'},
        ]
        result = subprocess.run([sys.executable, str(Path(p.__file__)), 'serve', '--state-dir', self.temp.name],
                                input=''.join(json.dumps(r) + '\n' for r in requests),
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(replies[2]['view']['timer'], '−01:00:00')
        self.assertEqual(replies[3]['view']['sequence'], 1)
        self.assertEqual(replies[4]['view']['phase'], 'off')
        self.assertFalse(replies[5]['ok'])
        self.assertFalse(replies[5]['retryable'])
        self.assertEqual(replies[5]['requestId'], 'stale-id')

    def test_reset_deletes_history_and_preserves_lock(self):
        self.transition('start', 7, rotate_bytes=1)
        self.transition('end', 23, rotate_bytes=1)
        self.transition('start', 31, rotate_bytes=1)
        inode = (self.store.root / '.lock').stat().st_ino
        state = self.store.reset('reset-1', '', 3)
        self.assertEqual(state, dict(p.blank_state(), generation='reset-1'))
        self.assertEqual(list(self.store.events.glob('*.jsonl')), [])
        self.assertEqual((self.store.root / '.lock').stat().st_ino, inode)
        self.assertEqual(p.Store(self.temp.name).recover(), state)

    def test_reset_retry_preserves_new_history_and_rejects_stale_commands(self):
        other = p.Store(self.temp.name)
        other.recover()
        self.store.reset('reset-1', '', 0)
        with self.assertRaisesRegex(ValueError, 'reset'):
            other.transition('start', 'stale', 0, now=at(7))
        self.store.transition('start', 'new', 0, now=at(8), expected_generation='reset-1')
        self.assertEqual(self.store.reset('reset-1', '', 0)['phase'], 'active')
        with self.assertRaisesRegex(ValueError, 'reset elsewhere'):
            other.reset('stale-reset', '', 0)
        with self.assertRaisesRegex(ValueError, 'another screen'):
            other.reset('stale-reset', 'reset-1', 0)

    def test_interrupted_reset_finishes_on_recovery(self):
        self.transition('start', 7)
        original_unlink = Path.unlink
        def fail_history(path, *args, **kwargs):
            if path.suffix == '.jsonl':
                raise OSError('interrupted deletion')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_history):
            with self.assertRaisesRegex(OSError, 'interrupted deletion'):
                self.store.reset('reset-1', '', 1)
        state = p.Store(self.temp.name).recover()
        self.assertEqual(state, dict(p.blank_state(), generation='reset-1'))
        self.assertFalse(self.store.reset_marker()['pending'])

    def test_server_can_reset_corrupt_history_at_startup(self):
        self.transition('start', 7)
        next(self.store.events.glob('*.jsonl')).write_text('{broken}\n')
        requests = [
            {'action': 'reset', 'requestId': 'reset-1', 'generation': '', 'sequence': 1},
            {'action': 'start', 'requestId': 'new', 'generation': 'reset-1', 'sequence': 0},
        ]
        result = subprocess.run([sys.executable, str(Path(p.__file__)), 'serve', '--state-dir', self.temp.name],
                                input=''.join(json.dumps(r) + '\n' for r in requests),
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertFalse(replies[0]['ok'])
        self.assertEqual(replies[1]['view']['sequence'], 0)
        self.assertEqual(replies[2]['view']['phase'], 'active')

    def test_invalid_transition_does_not_append_unreplayable_record(self):
        with self.assertRaisesRegex(ValueError, 'Invalid journal clock'):
            self.store.transition('start', 'invalid', 0, now={'utcMs': 0})
        self.assertEqual(list(self.store.events.glob('*.jsonl')), [])
        self.assertEqual(self.store.recover()['sequence'], 0)

    def test_invalid_reset_metadata_never_deletes_history(self):
        self.transition('start', 7)
        segment = next(self.store.events.glob('*.jsonl'))
        original = segment.read_bytes()
        for marker in [None, [], {}, {'generation': 'bad', 'pending': 'false'},
                       {'generation': '', 'pending': True}]:
            with self.subTest(marker=marker):
                (self.store.events / '.reset.json').write_text(json.dumps(marker))
                with self.assertRaisesRegex(ValueError, 'Invalid reset metadata'):
                    p.Store(self.temp.name).recover()
                self.assertEqual(segment.read_bytes(), original)

    def test_invalid_journal_values_block_replay_but_allow_reset(self):
        for field, value in [('clock', {}), ('clock', {'bootId': 'test', 'utcMs': 'bad', 'bootMs': 0}),
                             ('predictionMs', float('nan')), ('predictionMs', -1),
                             ('completedSample', {'eventId': 'sample', 'durationMs': float('inf')})]:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                store = p.Store(directory)
                store.transition('start', 'start', 0, now=at(7))
                segment = next(store.events.glob('*.jsonl'))
                event = json.loads(segment.read_text())
                event[field] = value
                segment.write_text(json.dumps(event) + '\n')
                with self.assertRaisesRegex(ValueError, 'Invalid record'):
                    p.Store(directory).recover()
                self.assertEqual(store.reset('reset', '', 0)['sequence'], 0)

    def test_xdg_root(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': self.temp.name}):
            self.assertEqual(p.state_root(), Path(self.temp.name) / 'omarchy/gregl83.plancks')
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.assertEqual(p.state_root(), Path.home() / '.local/state/omarchy/gregl83.plancks')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.process = subprocess.Popen([sys.executable, '-u', str(Path(p.__file__)),
                                         'serve', '--state-dir', self.temp.name],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop)
        self.buffer = b''
        self.assertTrue(self.read()['ok'])

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=3)
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()

    def read(self, timeout=3):
        deadline = time.monotonic() + timeout
        while b'\n' not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                self.fail('No response from helper')
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                self.fail('Helper exited: ' + self.process.stderr.read().decode())
            self.buffer += data
        line, self.buffer = self.buffer.split(b'\n', 1)
        return json.loads(line)

    def send(self, request):
        self.process.stdin.write((json.dumps(request) + '\n').encode())
        self.process.stdin.flush()

    def test_history_bridge_edit_updates_view_and_external_edits_refresh(self):
        self.send({'action': 'history', 'requestId': 'history-empty'})
        self.assertEqual(self.read()['history']['total'], 0)
        store = p.Store(self.temp.name)
        store.transition('start', 's1', 0, now=p.clock())
        self.read()
        store.transition('end', 'e1', 1, now=p.clock())
        self.read()
        self.send({'action': 'history', 'page': 0, 'requestId': 'history-full'})
        history = self.read()['history']
        self.assertEqual(history['rows'][0]['eventId'], 'e1')
        self.send({'action': 'set_inclusion', 'sampleId': 'e1', 'excludedFromLearning': True,
                   'requestId': 'edit', 'sequence': history['sequence'], 'generation': history['generation']})
        reply = self.read()
        self.assertTrue(reply['ok'])
        self.assertEqual(reply['requestId'], 'edit')
        self.assertEqual(reply['view']['workSampleCount'], 0)
        store.set_inclusion('e1', False, 'external-edit', 3)
        reply = self.read()
        self.assertEqual(reply['view']['workSampleCount'], 1)
        self.send({'action': 'history', 'requestId': 'history-updated'})
        reply = self.read()
        self.assertFalse(reply['history']['rows'][0]['excludedFromLearning'])

    def test_idle_sleeps_and_external_writer_wakes_it(self):
        self.assertFalse(select.select([self.process.stdout], [], [], 1.2)[0])
        store = p.Store(self.temp.name)
        store.transition('start', 'external', 0, now=p.clock())
        reply = self.read()
        self.assertEqual(reply['view']['phase'], 'active')
        tick = self.read()
        self.assertEqual(set(tick['patch']), {'timer'})
        self.assertTrue(tick['patch']['timer'].startswith('+'))

    def test_only_changed_fields_and_visible_panel_details(self):
        self.send({'action': 'start', 'requestId': 'start', 'sequence': 0})
        self.assertEqual(self.read()['requestId'], 'start')
        tick = self.read()
        self.assertEqual(set(tick['patch']), {'timer'})
        self.send({'action': 'panel', 'open': True})
        self.assertIn('elapsed', self.read()['view'])
        tick = self.read()
        self.assertEqual(set(tick['patch']), {'timer', 'elapsed'})
        self.send({'action': 'panel', 'open': False})
        self.assertIn('view', self.read())
        self.assertEqual(set(self.read()['patch']), {'timer'})

    def test_first_off_time_ticks_with_panel_closed(self):
        self.send({'action': 'start', 'requestId': 'start', 'sequence': 0})
        self.assertEqual(self.read()['requestId'], 'start')
        self.send({'action': 'end', 'requestId': 'end', 'sequence': 1})
        reply = self.read()
        self.assertEqual(reply['requestId'], 'end')
        self.assertTrue(reply['view']['timer'].startswith('+'))
        tick = self.read()
        self.assertEqual(set(tick['patch']), {'timer'})
        self.assertTrue(tick['patch']['timer'].startswith('+'))

    def test_external_reset_updates_idle_helper_and_keeps_watching(self):
        store = p.Store(self.temp.name)
        store.reset('reset-1', '', 0)
        self.assertEqual(self.read()['view']['generation'], 'reset-1')
        store.transition('start', 'new', 0, now=p.clock(), expected_generation='reset-1')
        self.assertEqual(self.read()['view']['phase'], 'active')

    def test_invalid_initial_duration_does_not_kill_helper(self):
        for value in [0.5, -1, True, 1e308]:
            self.send({'action': 'configure', 'initialSeconds': value})
            self.assertFalse(self.read()['ok'])
            self.assertTrue(self.read()['ok'])  # Existing state is still readable.
        self.send({'action': 'configure', 'initialSeconds': 3600})
        self.assertTrue(self.read()['ok'])
        self.send({'action': 'start', 'sequence': 0, 'requestId': 'valid-start'})
        self.assertEqual(self.read()['view']['timer'], '−01:00:00')

    def test_removing_history_reports_failure_instead_of_stale_state(self):
        Path(self.temp.name, 'events').rmdir()
        reply = self.read()
        self.assertFalse(reply['ok'])
        self.assertIn('moved or removed', reply['error'])



if __name__ == '__main__':
    unittest.main()
