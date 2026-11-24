"""Ensayos sintéticos reproducibles; las etiquetas nunca forman parte de las muestras."""
import csv
import json
import math
from pathlib import Path
import random

FIELDS = ('acquisition_time', 'voltage', 'current', 'rpm', 'temperature',
          'sensor_type', 'sensor_location', 'origin')
ANOMALY_KINDS = ('overcurrent', 'temperature', 'voltage_residual', 'combined', 'brief_peak')
FILENAMES = {
    'overcurrent': 'sobrecorriente',
    'temperature': 'temperatura',
    'voltage_residual': 'residual_estacionario',
    'combined': 'combinada',
    'brief_peak': 'pico_breve',
}
COPPER_ALPHA = 0.00393


def _timing(duration_s, step_s):
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (duration_s, step_s)):
        raise ValueError('Duración y paso deben ser finitos.')
    if duration_s <= 0 or step_s <= 0 or step_s > duration_s:
        raise ValueError('Se requiere 0 < paso <= duración.')
    return int(math.floor(duration_s / step_s + 1e-9)) + 1


def _rounded(value):
    return round(float(value), 12)


def modeled_voltage(current, rpm, temperature):
    """Calcula la tensión estacionaria coherente con la calibración eléctrica."""
    omega = math.tau * rpm / 60.0
    return 1.7 * current * (1 + COPPER_ALPHA * (temperature - 25.0)) + 0.09 * omega


def healthy_experiment(*, seed=20261104, duration_s=12.0, step_s=0.5, phase=0):
    """Genera un ensayo saludable con niveles escalonados y ruido local reproducible."""
    count = _timing(duration_s, step_s)
    if not isinstance(phase, int):
        raise ValueError('La fase debe ser un entero.')
    rng = random.Random(seed)
    rows = []
    for index in range(count):
        t = index * step_s
        current = 1.0 + 0.45 * ((index + phase) % 5) + rng.uniform(-0.005, 0.005)
        rpm = 300.0 + 70.0 * ((2 * index + phase) % 5) + rng.uniform(-0.05, 0.05)
        temperature = 25.0 + 0.2 * math.sin(t / 3.0) + rng.uniform(-0.02, 0.02)
        voltage = modeled_voltage(current, rpm, temperature)
        rows.append({
            'acquisition_time': _rounded(t),
            'voltage': _rounded(voltage),
            'current': _rounded(current),
            'rpm': _rounded(rpm),
            'temperature': _rounded(temperature),
            'sensor_type': 'sintetico',
            'sensor_location': 'bobinado',
            'origin': 'synthetic',
        })
    return rows


def _label(kind, signal, number, start_time, end_time, *, expect_alert=True):
    return {
        'id': f'{kind}-{signal}-{number}',
        'signal': signal,
        'start_time': _rounded(start_time),
        'end_time': _rounded(end_time),
        'origin': 'synthetic',
        'expect_alert': expect_alert,
    }


def anomaly_experiment(kind, *, seed=20261104, duration_s=12.0, step_s=0.5):
    """Devuelve (muestras, etiquetas); las etiquetas esperadas viajan por separado."""
    if kind not in ANOMALY_KINDS:
        raise ValueError('Tipo de anomalía desconocido: ' + ', '.join(ANOMALY_KINDS))
    rows = healthy_experiment(seed=seed, duration_s=duration_s, step_s=step_s)
    start_time = 3.0
    end_time = 6.0
    if end_time > duration_s:
        raise ValueError('Las anomalías requieren una duración mínima de 6 s.')
    labels = []
    for index, row in enumerate(rows):
        t = row['acquisition_time']
        active = start_time <= t < end_time
        brief = kind == 'brief_peak' and index == round(start_time / step_s)
        if (kind in ('overcurrent', 'combined') and active) or brief:
            row['current'] = _rounded(row['current'] + (4.0 if brief else 3.0))
        if kind in ('temperature', 'combined') and active:
            row['temperature'] = _rounded(row['temperature'] + 30.0)
        if kind != 'voltage_residual':
            row['voltage'] = _rounded(modeled_voltage(row['current'], row['rpm'], row['temperature']))
        elif active:
            row['voltage'] = _rounded(row['voltage'] + 2.0)
    if kind in ('overcurrent', 'combined'):
        labels.append(_label(kind, 'current', len(labels) + 1, start_time, end_time))
    if kind in ('temperature', 'combined'):
        labels.append(_label(kind, 'temperature', len(labels) + 1, start_time, end_time))
    if kind == 'voltage_residual':
        labels.append(_label(kind, 'voltage_residual', 1, start_time, end_time))
    if kind == 'brief_peak':
        labels.append(_label(kind, 'current', 1, start_time, start_time + step_s, expect_alert=False))
    return rows, labels


def _write_rows(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _write_labels(path, labels):
    path.write_text(json.dumps(labels, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_corpus(directory, *, seed=20261104):
    """Escribe tres ensayos saludables y cinco anomalías con etiquetas independientes."""
    root = Path(directory)
    labels_dir = root / 'labels'
    labels_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    filenames = {
        'ajuste': 'ajuste_saludable_sintetico.csv',
        'validacion': 'validacion_saludable_sintetica.csv',
        'evaluacion_saludable': 'evaluacion_saludable_sintetica.csv',
    }
    for name, phase, offset in (('ajuste', 0, 0), ('validacion', 2, 1),
                                ('evaluacion_saludable', 4, 7)):
        path = root / filenames[name]
        _write_rows(path, healthy_experiment(seed=seed + offset, phase=phase))
        labels_path = None
        if name == 'evaluacion_saludable':
            labels_path = labels_dir / f'{name}.json'
            _write_labels(labels_path, [])
        manifest[name] = {'data': str(path), 'labels': str(labels_path) if labels_path else None}
    for offset, kind in enumerate(ANOMALY_KINDS, 2):
        rows, labels = anomaly_experiment(kind, seed=seed + offset)
        name = FILENAMES[kind]
        data_path = root / f'{name}.csv'
        labels_path = labels_dir / f'{name}.json'
        _write_rows(data_path, rows)
        _write_labels(labels_path, labels)
        manifest[kind] = {'data': str(data_path), 'labels': str(labels_path)}
    return manifest
