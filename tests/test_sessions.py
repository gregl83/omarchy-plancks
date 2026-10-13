import copy
import json
from pathlib import Path
import tempfile
import os
import select
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

import plancks
import sessions


def clock(ms, boot='test'):
    return dict(utcMs=1700000000000 + ms, bootId=boot, bootMs=ms)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = plancks.Store(self.temp.name)
        self.state, _ = self.store.transition('start', 'epoch', 0, now=clock(0))
        self.config = dict(sessions.DEFAULTS, preset='custom', focusMinutes=1, shortBreakMinutes=1,
                           longBreakMinutes=2, rounds=2, longBreakEvery=2)

    def command(self, action, ms=0, **kwargs):
        current = self.state['session']
        args = dict(session_id=current['sessionId'], stage_id=current['stages'][current['index']]['stageId']) if current else {}
        args.update(kwargs)
        self.state, _ = self.store.session_action(action, action + str(self.state['sequence']),
            self.state['sequence'], self.state['generation'], now=clock(ms), **args)
        return self.state

    def start(self):
        return self.command('session_started', config=self.config)

    def test_cli_start_retry_and_explicit_epoch_cascade(self):
        def run(action, sequence, *extra, ok=True):
            result = subprocess.run([sys.executable, str(Path(plancks.__file__)), action,
                '--state-dir', self.temp.name, '--sequence', str(sequence), *extra],
                capture_output=True, text=True, timeout=10)
            payload = json.loads(result.stdout)
            self.assertEqual(payload['ok'], ok, payload)
            self.assertEqual(result.returncode, 0 if ok else 1)
            return payload.get('view')

        run('session-start', 1, '--request-id', 'cli-session')
        run('session-start', 1, '--request-id', 'cli-session')
        run('session-pause', 2)
        run('session-resume', 3)
        run('end', 4, ok=False)
        result = run('end', 4, '--cascade-session', 'cli-session')
        self.assertIsNone(result['session'])
        self.assertEqual(self.store.recover()['phase'], 'off')

    def test_custom_name_persistence_search_and_legacy_configuration(self):
        self.config['name'] = '  Reading & notes  '
        self.start()
        target = self.state['session']['sessionId']
        self.assertEqual(self.state['session']['config']['name'], 'Reading & notes')
        live = sessions.live(self.state['session'], clock(1000))
        self.assertEqual(live['name'], 'Reading & notes')
        self.assertIn('Activity', live['caption'])
        self.assertEqual(live['nextLabel'], 'Start rest')
        retry, _ = self.store.session_action('session_started', target, 1, config=self.config)
        self.assertEqual(retry['sequence'], self.state['sequence'])
        self.config['name'] = 'Another session'
        self.command('session_advanced', 60000)
        self.assertEqual(sessions.live(self.state['session'], clock(60000))['nextLabel'], 'Start activity')
        self.command('session_stopped', 65000)
        restored = plancks.Store(self.temp.name).recover()
        self.assertEqual(restored['sessions'][0]['config']['name'], 'Reading & notes')
        self.assertEqual(self.store.session_history(query='reading notes')['total'], 1)
        self.assertEqual(self.store.session_history(query='activity')['total'], 1)
        self.assertEqual(self.store.session_history(query='rest')['total'], 1)
        self.assertNotIn('name', sessions.configuration(dict(sessions.DEFAULTS)))
        self.assertEqual(sessions.configuration(dict(sessions.DEFAULTS, name=''))['name'], '')
        for name in (None, 123, 'x' * 81, 'a\nb', 'a\tb', 'a\u2028b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                sessions.configuration(dict(self.config, name=name))
        with self.assertRaises(ValueError):
            sessions.configuration(dict(sessions.DEFAULTS, name='Reading'))

    def test_config_sequence_and_presets(self):
        for final, expected in ((False, ['focus', 'short_break', 'focus']),
                                (True, ['focus', 'short_break', 'focus', 'long_break'])):
            config = dict(self.config, finalBreak=final)
            self.assertEqual([s['kind'] for s in sessions.stages(config)], expected)
        self.assertEqual(len(sessions.stages(dict(self.config, rounds=1, finalBreak=False))), 1)
        for key, value in [('rounds', 0), ('rounds', True), ('focusMinutes', 1.5),
                           ('longBreakEvery', 13), ('finalBreak', 1), ('preset', 'pomodoro')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                sessions.configuration(dict(self.config, **{key: value}))

    def test_countdown_overrun_pause_and_manual_finish(self):
        self.config.update(rounds=1, finalBreak=False)
        self.start()
        current = lambda ms: sessions.live(self.state['session'], clock(ms))
        self.assertEqual(current(0)['timer'], '−00:01:00')
        self.assertEqual(current(60000)['timer'], '+00:00:00')
        self.assertEqual(current(65000)['timer'], '+00:00:05')
        self.command('session_paused', 65000)
        self.assertEqual(current(90000)['timer'], '+00:00:05')
        self.command('session_resumed', 95000)
        self.assertEqual(current(100000)['timer'], '+00:00:10')
        self.command('session_completed', 100000)
        row = sessions.summary(self.state['sessions'][0])
        self.assertEqual(row['focusMs'], 70000)
        self.assertEqual(row['pausedMs'], 30000)
        self.assertEqual(row['stages'][0]['differenceMs'], 10000)
        self.assertIsNone(self.state['session'])
        self.assertEqual(self.state['phase'], 'active')
        self.assertEqual(self.state['workSamples'], [])

    def test_replay_uses_saved_preset_values(self):
        self.config = dict(sessions.DEFAULTS)
        self.start()
        with patch.dict(sessions.DEFAULTS, focusMinutes=50):
            restored = plancks.Store(self.temp.name).recover()['session']
        self.assertEqual(restored['config']['focusMinutes'], 25)
        self.assertEqual(restored['stages'][0]['plannedMs'], 25 * 60000)

    def test_full_rounds_and_final_break(self):
        self.start()
        for ms in (70000, 150000, 230000):
            self.command('session_advanced', ms)
            self.assertEqual(sessions.live(self.state['session'], clock(ms))['actualMs'], 0)
        self.assertEqual(self.state['session']['stages'][3]['kind'], 'long_break')
        with self.assertRaises(ValueError):
            self.command('session_completed', 300000)
        self.command('session_completed', 360000)
        row = sessions.summary(self.state['sessions'][0])
        self.assertEqual(row['completedRounds'], 2)
        self.assertEqual(row['focusMs'], 150000)
        self.assertEqual(row['breakMs'], 210000)
        self.assertEqual(len(self.store.session_history(query='long break completed')['rows']), 1)

    def test_guards_stop_cascade_and_learning(self):
        self.start()
        with self.assertRaises(ValueError):
            self.command('session_started', config=self.config)
        with self.assertRaises(ValueError):
            self.command('session_advanced', 30000)
        with self.assertRaisesRegex(ValueError, 'Session active'):
            self.store.transition('end', 'end', self.state['sequence'], now=clock(30000))
        before = self.state['sequence']
        self.state, _ = self.store.transition('end', 'end', before, now=clock(30000),
            cascade_session_id=self.state['session']['sessionId'])
        self.assertEqual(self.state['sequence'], before + 1)
        self.assertEqual(self.state['phase'], 'off')
        self.assertEqual(self.state['sessions'][0]['reason'], 'epoch-ended')
        self.assertEqual(len(self.state['workSamples']), 1)
        self.assertEqual(self.store.recover(), self.state)
        with self.assertRaises(ValueError):
            self.command('session_started', config=self.config)

    def test_restart_sleep_paused_and_no_tick_io(self):
        self.start()
        state = self.store.recover()
        display = plancks.Display(state, now=clock(0))
        with patch.object(self.store, 'load', side_effect=AssertionError('tick IO')):
            self.assertEqual(display.update(clock(7200000))['session']['timer'], '+01:59:00')
            self.assertEqual(display.update(clock(7200000, 'reboot'))['session']['timer'], '+01:59:00')
        self.command('session_paused', 30000)
        state = plancks.Store(self.temp.name).recover()
        self.assertEqual(sessions.live(state['session'], clock(7200000, 'reboot'))['timer'], '−00:00:30')
        self.assertFalse(sessions.live(state['session'], clock(7200000))['targetDue'])

    def test_retry_claim_reset_and_legacy_replay(self):
        self.start()
        first = copy.deepcopy(self.state)
        # Replay the start command without creating another session.
        state, _ = self.store.session_action('session_started', 'session_started1', 1, config=self.config, now=clock(999))
        self.assertEqual(state, first)
        args = dict(session_id=first['session']['sessionId'], stage_id=first['session']['stages'][0]['stageId'])
        self.state, _ = self.store.session_action('session_stage_target_reached', 'target', first['sequence'], now=clock(60000), **args)
        with self.assertRaisesRegex(ValueError, 'claimed'):
            plancks.Store(self.temp.name).session_action('session_stage_target_reached', 'target', first['sequence'], now=clock(70000), **args)
        self.assertFalse(sessions.live(self.state['session'], clock(70000))['targetDue'])
        self.store.reset('reset', '', self.state['sequence'])
        with self.assertRaisesRegex(ValueError, 'reset'):
            self.store.session_action('session_stopped', 'stale', self.state['sequence'], **args)
        self.assertEqual(self.store.recover()['sessions'], [])

    def test_corrupt_version_parent_and_stage_rejected(self):
        self.start()
        for update in ({'schemaVersion': 1}, {'epochId': 'other'}, {'stageId': 'other'}):
            event = dict(schemaVersion=2, type='session_stopped', eventId='bad', sequence=3,
                         clock=clock(1000), epochId='epoch', sessionId=self.state['session']['sessionId'],
                         stageId=self.state['session']['stages'][0]['stageId'])
            event.update(update)
            with self.assertRaises(ValueError):
                plancks.apply(copy.deepcopy(self.state), event)

    def test_clock_backwards_never_awards_completed_focus(self):
        self.start()
        self.command('session_paused', 30000)
        self.command('session_resumed', 20000)
        with self.assertRaises(ValueError):
            self.command('session_advanced', 120000)
        self.command('session_stopped', 120000)
        row = sessions.summary(self.state['sessions'][0])
        self.assertTrue(row['invalid'])
        self.assertEqual(row['focusMs'], 0)


    def test_parallel_target_claims_and_stale_commands(self):
        self.start()
        current = self.state['session']
        stage = current['stages'][0]['stageId']
        def claim(_):
            try:
                plancks.Store(self.temp.name).session_action('session_stage_target_reached', sessions.target_id(stage),
                    self.state['sequence'], session_id=current['sessionId'], stage_id=stage, now=clock(60000))
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(claim, range(2))), 1)
        # A milestone alone must not make an otherwise-current user action stale.
        self.state, _ = self.store.session_action('session_paused', 'pause', self.state['sequence'],
            session_id=current['sessionId'], stage_id=stage, now=clock(65000))
        with self.assertRaises(ValueError):
            self.store.session_action('session_stopped', 'stale', 1,
                session_id=current['sessionId'], stage_id=stage, now=clock(65000))

    def test_snapshot_failure_torn_tail_and_retry(self):
        self.start()
        current = self.state['session']
        args = dict(session_id=current['sessionId'], stage_id=current['stages'][0]['stageId'])
        with patch.object(self.store, 'snapshot', side_effect=OSError('disk full')):
            state, warning = self.store.session_action('session_stopped', 'stop', self.state['sequence'], now=clock(12000), **args)
        self.assertIn('snapshot', warning)
        state, _ = plancks.Store(self.temp.name).session_action('session_stopped', 'stop', self.state['sequence'], now=clock(99999), **args)
        self.assertEqual(len(state['sessions']), 1)
        self.assertEqual(state['sessions'][0]['stages'][0]['actualMs'], 12000)
        segment = next(self.store.events.glob('events-*.jsonl'))
        with segment.open('ab') as stream:
            stream.write(b'{"schemaVersion":2')
        fresh = plancks.Store(self.temp.name)
        state = fresh.recover()
        fresh.session_action('session_started', 'another', state['sequence'], config=self.config, now=clock(20000))
        self.assertEqual(len(list(self.store.events.glob('events-*.jsonl'))), 2)
        self.assertEqual(len(fresh.recover()['sessions']), 1)

    def test_session_inclusion_replay_stats_and_independence(self):
        self.start()
        target = self.state['session']['sessionId']
        self.command('session_advanced', 70000)
        self.command('session_stopped', 80000)
        before = copy.deepcopy(self.state)
        original = self.store.session_history()
        self.assertEqual(original['completedRounds'], 1)
        self.assertEqual(original['completedFocusMs'], 70000)
        seq = self.state['sequence']
        args = dict(session_id=target, excluded=True)
        self.state, _ = self.store.session_action('session_inclusion_changed', 'exclude', seq, **args)
        page = self.store.session_history()
        self.assertEqual((page['completedRounds'], page['completedFocusMs'], page['bestRounds']), (0, 0, 0))
        self.assertEqual(page['total'], 1)
        self.assertTrue(page['rows'][0]['excludedFromStatistics'])
        self.assertTrue(page['trend'][0]['excludedFromLearning'])
        self.assertEqual(page['trend'][0]['durationMs'], 70000)
        self.assertEqual(self.store.session_history(query='excluded')['total'], 1)
        replay = plancks.Store(self.temp.name)
        saved = replay.recover()
        self.assertTrue(saved['sessions'][0]['excludedFromStatistics'])
        for key in ('workSamples', 'gapSamples', 'predictionMs', 'deadlineUtcMs'):
            self.assertEqual(saved[key], before[key])
        self.assertEqual(saved['sessions'][0]['stages'], before['sessions'][0]['stages'])
        retried, _ = replay.session_action('session_inclusion_changed', 'exclude', seq, **args)
        self.assertEqual(retried['sequence'], saved['sequence'])
        with self.assertRaises(ValueError):
            replay.session_action('session_inclusion_changed', 'exclude', seq, session_id=target, excluded=False)
        with self.assertRaises(ValueError):
            replay.session_action('session_inclusion_changed', 'stale', seq, session_id=target, excluded=False)
        # Inclusion can also be changed while the parent epoch is closed.
        saved, _ = replay.transition('end', 'close-parent', saved['sequence'], now=clock(90000), skip_learning=True)
        saved, _ = replay.session_action('session_inclusion_changed', 'include', saved['sequence'], session_id=target, excluded=False)
        page = replay.session_history()
        self.assertEqual(page['bestRounds'], 1)
        self.assertFalse(page['trend'][0]['excludedFromLearning'])
        self.assertEqual(saved['workSamples'], [])
        for target_id, value in [('missing', True), (target, 1)]:
            with self.assertRaises(ValueError):
                replay.session_action('session_inclusion_changed', 'bad', saved['sequence'], session_id=target_id, excluded=value)
        with self.assertRaises(ValueError):
            replay.session_action('session_inclusion_changed', 'reset', saved['sequence'], 'wrong-generation', session_id=target, excluded=True)

    def test_invalid_and_active_sessions_cannot_be_included(self):
        self.start()
        target = self.state['session']['sessionId']
        with self.assertRaises(ValueError):
            self.store.session_action('session_inclusion_changed', 'active', self.state['sequence'], session_id=target, excluded=True)
        self.command('session_stopped', -1000)
        with self.assertRaises(ValueError):
            self.store.session_action('session_inclusion_changed', 'invalid', self.state['sequence'], session_id=target, excluded=False)

    def test_focus_trend_uses_actual_focus_and_ignores_search(self):
        self.start()
        self.command('session_paused', 20000)
        self.command('session_resumed', 30000)
        self.command('session_advanced', 80000)
        self.command('session_stopped', 90000)
        trend = self.store.session_history()['trend']
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]['durationMs'], 70000)
        self.assertTrue(trend[0]['stopped'])
        self.assertEqual(trend[0]['completedRounds'], 1)
        self.assertEqual(trend[0]['rounds'], 2)
        self.assertEqual(self.store.session_history(query='nonexistent')['trend'], trend)
        for i in range(12):
            self.start()
            self.command('session_stopped', 100000 + i)
        recent = self.store.session_history()['trend']
        self.assertEqual(len(recent), 10)
        self.assertEqual([p['endUtcMs'] for p in recent], sorted(p['endUtcMs'] for p in recent))

    def test_history_pagination_search_and_epoch_exclusion_independence(self):
        for i in range(7):
            self.start()
            self.command('session_stopped', 1000)
        page = self.store.session_history(1)
        self.assertEqual((page['total'], page['pages'], len(page['rows'])), (7, 2, 2))
        self.assertEqual(self.store.session_history(query='nonexistent')['total'], 0)
        self.assertEqual(self.store.session_history(query='custom stopped')['total'], 7)
        self.state, _ = self.store.transition('end', 'end', self.state['sequence'], now=clock(5000), skip_learning=True)
        self.assertEqual(self.state['workSamples'], [])
        self.assertEqual(self.store.session_history()['total'], 7)


class SessionBridgeTests(unittest.TestCase):
    def test_target_notification_once_across_restart_and_no_per_tick_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = plancks.Store(directory)
            now = plancks.clock()
            earlier = dict(now, utcMs=now['utcMs'] - 61000, bootMs=now['bootMs'] - 61000)
            state, _ = store.transition('start', 'epoch', 0, now=earlier)
            config = dict(sessions.DEFAULTS, preset='custom', rounds=1, focusMinutes=1, finalBreak=False)
            store.session_action('session_started', 'session', state['sequence'], config=config, now=earlier)
            def collect():
                process = subprocess.Popen([sys.executable, str(Path(plancks.__file__)), 'serve', '--state-dir', directory],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                buffer, messages = b'', []
                try:
                    deadline = time.monotonic() + 2.2
                    while time.monotonic() < deadline:
                        if select.select([process.stdout], [], [], 0.2)[0]:
                            buffer += os.read(process.stdout.fileno(), 65536)
                            while b'\n' in buffer:
                                line, buffer = buffer.split(b'\n', 1)
                                messages.append(json.loads(line))
                    process.stdin.close()
                    process.wait(timeout=3)
                    self.assertEqual(process.returncode, 0, process.stderr.read().decode())
                    return messages
                finally:
                    if process.poll() is None:
                        process.kill(); process.wait()
                    process.stdout.close(); process.stderr.close()
            first = collect()
            self.assertEqual(sum('sessionNotice' in m for m in first), 1)
            self.assertTrue(any(m.get('view', {}).get('session', {}).get('timer', '').startswith('+') for m in first))
            before = [(p.name, p.stat().st_mtime_ns) for p in store.events.glob('events-*.jsonl')]
            second = collect()
            self.assertEqual(sum('sessionNotice' in m for m in second), 0)
            self.assertEqual(before, [(p.name, p.stat().st_mtime_ns) for p in store.events.glob('events-*.jsonl')])
            self.assertEqual(store.recover()['session']['status'], 'running')


if __name__ == '__main__':
    unittest.main()
