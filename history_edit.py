"""Apply reversible, shared-boundary corrections to completed intervals."""
import copy


def correct(state, sample_id, start_ms, end_ms, now_ms):
    rows = state['history']
    index = next((i for i, row in enumerate(rows) if row['eventId'] == sample_id), None)
    if index is None:
        raise ValueError('That interval is no longer available. Reopen history.')
    if any(type(value) is not int or not 0 <= value <= 253402300799999
           for value in (start_ms, end_ms)):
        raise ValueError('Enter valid dates and times.')
    if end_ms <= start_ms:
        raise ValueError('End must be after start.')
    if end_ms > now_ms:
        raise ValueError('A completed interval cannot end in the future.')
    row = rows[index]
    changes = []
    if start_ms != row['start']['utcMs']:
        if index and start_ms <= rows[index - 1]['start']['utcMs']:
            raise ValueError('Start must be after the preceding interval starts.')
        changes.append((index, 'start', start_ms))
        if index:
            changes.append((index - 1, 'end', start_ms))
    if end_ms != row['end']['utcMs']:
        if index + 1 < len(rows) and end_ms >= rows[index + 1]['end']['utcMs']:
            raise ValueError('End must be before the following interval ends.')
        changes.append((index, 'end', end_ms))
        if index + 1 < len(rows):
            changes.append((index + 1, 'start', end_ms))
    for position, edge, value in changes:
        sample = rows[position]
        if 'originalTimes' not in sample:
            sample['originalTimes'] = copy.deepcopy({key: sample[key] for key in
                                                    ('start', 'end', 'durationMs', 'timeBasis')})
        previous = sample[edge]
        # Preserve suspend-inclusive elapsed-time behavior for a corrected anchor.
        sample[edge] = dict(previous, utcMs=value, bootMs=previous['bootMs'] + value - previous['utcMs'])
    for position in {entry[0] for entry in changes}:
        sample = rows[position]
        original = sample['originalTimes']
        sample['edited'] = any(sample[key]['utcMs'] != original[key]['utcMs'] for key in ('start', 'end'))
        sample['durationMs'] = sample['end']['utcMs'] - sample['start']['utcMs'] if sample['edited'] else original['durationMs']
        sample['timeBasis'] = 'manual' if sample['edited'] else original['timeBasis']
    if changes:
        # Keep the open interval attached to the final completed boundary.
        state['anchor'] = copy.deepcopy(rows[-1]['end'])
        for kind, key in (('epoch', 'lastEnd'), ('off', 'lastStart')):
            latest = next((s for s in reversed(rows) if s['kind'] == kind), None)
            if latest:
                state[key] = copy.deepcopy(latest['end'])
        if not any(s['kind'] == 'off' for s in rows):
            state['lastStart'] = copy.deepcopy(rows[-1]['start'])
