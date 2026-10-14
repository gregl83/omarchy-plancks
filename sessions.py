"""Pure session configuration, journal reduction, and live projections."""
import copy
import uuid

DEFAULTS = dict(preset='pomodoro', presetVersion=1, focusMinutes=25,
                shortBreakMinutes=5, longBreakMinutes=15, longBreakEnabled=True,
                longBreakEvery=4, rounds=4, finalBreak=True)


def target_id(stage_id):
    return 'session-target-' + str(uuid.uuid5(uuid.NAMESPACE_URL, stage_id))


def configuration(value, replay=False):
    if not isinstance(value, dict) or set(value) - {'name'} != set(DEFAULTS):
        raise ValueError('A complete session configuration is required')
    for key in ('focusMinutes', 'shortBreakMinutes', 'longBreakMinutes', 'longBreakEvery', 'rounds'):
        limit = 12 if key in ('rounds', 'longBreakEvery') else 180
        if type(value[key]) is not int or not 1 <= value[key] <= limit:
            raise ValueError(f'{key} must be a whole number from 1 to {limit}')
    if any(type(value[k]) is not bool for k in ('longBreakEnabled', 'finalBreak')):
        raise ValueError('Rest options must be booleans')
    if value['preset'] not in ('pomodoro', 'custom') or type(value['presetVersion']) is not int or value['presetVersion'] != 1:
        raise ValueError('Unsupported session preset')
    name = value.get('name', '')
    if not isinstance(name, str) or len(name) > 80 or any(ord(c) < 32 or ord(c) == 127 or c in '\u2028\u2029' for c in name):
        raise ValueError('Session name must be at most 80 characters on one line')
    if value['preset'] == 'pomodoro' and name.strip():
        raise ValueError('Named sessions must use Custom')
    if not replay and value['preset'] == 'pomodoro' and {k: v for k, v in value.items() if k != 'name'} != DEFAULTS:
        raise ValueError('Edited Pomodoro values must use Custom')
    return dict(value, name=name.strip()) if "name" in value else dict(value)


def stages(config):
    result = []
    for number in range(1, config['rounds'] + 1):
        result.append(dict(kind='focus', round=number, plannedMs=config['focusMinutes'] * 60000))
        if number < config['rounds'] or config['finalBreak']:
            long = config['longBreakEnabled'] and number % config['longBreakEvery'] == 0
            result.append(dict(kind='long_break' if long else 'short_break', round=number,
                               plannedMs=config['longBreakMinutes' if long else 'shortBreakMinutes'] * 60000))
    return result


def elapsed(a, b):
    key = 'bootMs' if a['bootId'] == b['bootId'] else 'utcMs'
    return b[key] - a[key]


def running_ms(session, now):
    stage = session['stages'][session['index']]
    return stage['runningMs'] + (elapsed(stage['anchor'], now) if session['status'] == 'running' else 0)


def activate(session, now):
    stage = session['stages'][session['index']]
    stage.update(start=now, anchor=now, runningMs=0, pausedMs=0, targetReached=False, invalid=False)


def settle(session, now):
    stage = session['stages'][session['index']]
    delta = elapsed(stage['anchor'], now)
    stage['invalid'] = stage['invalid'] or delta < 0
    stage['runningMs' if session['status'] == 'running' else 'pausedMs'] += max(0, delta)
    stage['anchor'] = now
    return stage


def close_stage(session, now, outcome):
    stage = settle(session, now)
    stage.update(end=now, outcome=outcome, actualMs=stage['runningMs'],
                 differenceMs=stage['runningMs'] - stage['plannedMs'],
                 overrunMs=max(0, stage['runningMs'] - stage['plannedMs']))


def stop(state, now, reason):
    session = state['session']
    close_stage(session, now, 'stopped')
    session.update(status='stopped', end=now, reason=reason)
    state['sessions'].append(session)
    state['session'] = None


def reduce(state, event):
    action = event['type']
    now = event['clock']
    session = state['session']
    if action == 'session_inclusion_changed':
        target = event.get('sessionId')
        excluded = event.get('excludedFromStatistics')
        if not isinstance(target, str) or type(excluded) is not bool:
            raise ValueError('Invalid session inclusion change')
        saved = next((s for s in state['sessions'] if s['sessionId'] == target), None)
        if saved is None or summary(saved)['invalid']:
            raise ValueError('Unknown or invalid history session')
        saved['excludedFromStatistics'] = excluded
        return
    if state['phase'] != 'active' or event['epochId'] != state['epochId']:
        raise ValueError('Session requires its active parent epoch')
    if action == 'session_started':
        if session:
            raise ValueError('A session is already active')
        config = configuration(event['config'], replay=True)
        sequence = event['stages']
        if sequence != stages(config):
            raise ValueError('Invalid saved session stage sequence')
        session = dict(sessionId=event['eventId'], epochId=state['epochId'], config=config,
                       stages=copy.deepcopy(sequence), index=0, status='running', start=now, epochStart=state['anchor'])
        for index, stage in enumerate(session['stages']):
            stage['stageId'] = f"{session['sessionId']}:{index}"
        activate(session, now)
        state['session'] = session
        return
    if not session or event.get('sessionId') != session['sessionId'] or event.get('stageId') != session['stages'][session['index']]['stageId']:
        raise ValueError('Session or stage changed; review the current timer')
    stage = session['stages'][session['index']]
    if action == 'session_stage_target_reached':
        if stage['targetReached'] or stage['invalid'] or elapsed(stage['anchor'], now) < 0 or running_ms(session, now) < stage['plannedMs']:
            raise ValueError('Stage target is not due')
        stage['targetReached'] = True
    elif action == 'session_paused':
        if session['status'] != 'running':
            raise ValueError('Session is already paused')
        settle(session, now)
        session['status'] = 'paused'
    elif action == 'session_resumed':
        if session['status'] != 'paused':
            raise ValueError('Session is not paused')
        settle(session, now)
        session['status'] = 'running'
    elif action in ('session_advanced', 'session_completed'):
        if stage['invalid'] or elapsed(stage['anchor'], now) < 0 or running_ms(session, now) < stage['plannedMs']:
            raise ValueError('Reach the stage target before advancing; Stop is available')
        final = session['index'] == len(session['stages']) - 1
        if final != (action == 'session_completed'):
            raise ValueError('Use Finish session only for the final stage')
        close_stage(session, now, 'completed')
        if final:
            session.update(status='completed', end=now, reason='finished')
            state['sessions'].append(session)
            state['session'] = None
        else:
            session['index'] += 1
            session['status'] = 'running'
            activate(session, now)
    elif action == 'session_stopped':
        stop(state, now, 'user')
    else:
        raise ValueError('Unknown session event')


def duration(ms):
    seconds = max(0, int(ms) // 1000)
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


def live(session, now):
    if not session:
        return None
    stage = session['stages'][session['index']]
    actual = running_ms(session, now)
    invalid = stage['invalid'] or actual < 0 or (session['status'] == 'running' and elapsed(stage['anchor'], now) < 0)
    delta = actual // 1000 - stage['plannedMs'] // 1000
    final = session['index'] == len(session['stages']) - 1
    next_label = 'Finish session' if final else ('Start rest' if stage['kind'] == 'focus' else 'Start activity')
    label = {'focus': 'Activity', 'short_break': 'Rest', 'long_break': 'Long rest'}[stage['kind']]
    return dict(sessionId=session['sessionId'], stageId=stage['stageId'], epochId=session['epochId'],
                name=session['config'].get('name', ''), status=session['status'], kind=stage['kind'], round=stage['round'], rounds=session['config']['rounds'],
                timer='--:--:--' if invalid else ('−' if delta < 0 else '+') + duration(abs(delta) * 1000),
                caption=label + f" · round {stage['round']} of {session['config']['rounds']}" + (' · Clock changed' if invalid else ' · Overrun' if delta > 0 else '') + (' · Paused' if session['status'] == 'paused' else '') + (' · ' + session['config']['name'] if session['config'].get('name') else ''),
                canAdvance=not invalid and delta >= 0, final=final, nextLabel=next_label,
                targetDue=not invalid and actual >= stage['plannedMs'] and not stage['targetReached'],
                invalid=invalid, plannedMs=stage['plannedMs'], actualMs=max(0, actual))


def summary(session):
    result = copy.deepcopy(session)
    done = [s for s in session['stages'] if 'outcome' in s]
    valid = [s for s in done if not s['invalid']]
    result.update(completedRounds=sum(s['kind'] == 'focus' and s['outcome'] == 'completed' for s in valid),
                  focusMs=sum(s['actualMs'] for s in valid if s['kind'] == 'focus'),
                  completedFocusMs=sum(s['actualMs'] for s in valid if s['kind'] == 'focus' and s['outcome'] == 'completed'),
                  partialFocusMs=sum(s['actualMs'] for s in valid if s['kind'] == 'focus' and s['outcome'] != 'completed'),
                  breakMs=sum(s['actualMs'] for s in valid if s['kind'] != 'focus'),
                  pausedMs=sum(s['pausedMs'] for s in valid), invalid=any(s['invalid'] for s in done))
    return result
