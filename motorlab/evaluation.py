"""Evaluación independiente de episodios frente a etiquetas externas."""
from collections.abc import Mapping
import math


def _validated(items, name):
    if isinstance(items, (str, bytes, Mapping)):
        raise ValueError(f'{name} debe ser una secuencia de registros.')
    records = list(items)
    ids = set()
    for item in records:
        if not isinstance(item, Mapping):
            raise ValueError(f'Cada registro de {name} debe ser un mapeo.')
        missing = {'id', 'signal', 'start_time', 'end_time'} - set(item)
        if missing:
            raise ValueError(f'Faltan campos en {name}: ' + ', '.join(sorted(missing)))
        identifier = item['id']
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError(f'Los IDs de {name} deben ser textos únicos y no vacíos.')
        if not isinstance(item['signal'], str) or not item['signal']:
            raise ValueError(f'La señal de {identifier} debe ser texto no vacío.')
        start, end = item['start_time'], item['end_time']
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                   for value in (start, end)):
            raise ValueError(f'El intervalo de {identifier} debe ser finito.')
        if start < 0 or end < start:
            raise ValueError(f'El intervalo de {identifier} es inválido.')
        if 'expect_alert' in item and not isinstance(item['expect_alert'], bool):
            raise ValueError(f'expect_alert de {identifier} debe ser booleano.')
        ids.add(identifier)
    return records


def _overlaps(first, second):
    return first['start_time'] <= second['end_time'] and first['end_time'] >= second['start_time']


def evaluate_episodes(episodes, labels):
    """Maximiza correspondencias por señal/solapamiento; expect_alert=false no exige alarma."""
    detected_episodes = _validated(episodes, 'episodios')
    expected_labels = _validated(labels, 'etiquetas')
    required = sorted((label for label in expected_labels if label.get('expect_alert', True)),
                      key=lambda item: (item['start_time'], item['end_time'], item['id']))
    not_expected = [label for label in expected_labels if not label.get('expect_alert', True)]
    candidates = []
    for label in required:
        matches = [index for index, episode in enumerate(detected_episodes)
                   if episode['signal'] == label['signal'] and _overlaps(episode, label)]
        candidates.append(sorted(matches, key=lambda index: (
            max(0.0, detected_episodes[index]['start_time'] - label['start_time']),
            detected_episodes[index]['start_time'], detected_episodes[index]['id'])))

    episode_matches = {}

    def assign(label_index, visited):
        for episode_index in candidates[label_index]:
            if episode_index in visited:
                continue
            visited.add(episode_index)
            if episode_index not in episode_matches or assign(episode_matches[episode_index], visited):
                episode_matches[episode_index] = label_index
                return True
        return False

    for label_index in range(len(required)):
        assign(label_index, set())
    label_matches = {label_index: episode_index
                     for episode_index, label_index in episode_matches.items()}
    detections = []
    missed = []
    for label_index, label in enumerate(required):
        if label_index not in label_matches:
            missed.append(label['id'])
            continue
        episode = detected_episodes[label_matches[label_index]]
        detections.append({
            'label_id': label['id'],
            'episode_id': episode['id'],
            'signal': label['signal'],
            'delay_s': max(0.0, episode['start_time'] - label['start_time']),
        })
    false_alerts = sorted(episode['id'] for index, episode in enumerate(detected_episodes)
                          if index not in episode_matches)
    delays = [item['delay_s'] for item in detections]
    return {
        'detections': detections,
        'missed': sorted(missed),
        'false_alerts': false_alerts,
        'not_expected': sorted(label['id'] for label in not_expected),
        'detection_count': len(detections),
        'missed_count': len(missed),
        'false_alert_count': len(false_alerts),
        'mean_delay_s': sum(delays) / len(delays) if delays else None,
    }
