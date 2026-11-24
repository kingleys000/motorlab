"""Importación estricta de ensayos, sin inferir datos no observados."""
import csv
import math
from pathlib import Path

REQUIRED = ('acquisition_time', 'voltage', 'current', 'rpm', 'temperature',
            'sensor_type', 'sensor_location')
OPTIONAL = ('load', 'ambient')


def read_experiment(path, *, origin=None):
    """Leer CSV con tiempo relativo en segundos y unidades SI; no altera el archivo."""
    if origin is not None and origin not in ('measured', 'synthetic'):
        raise ValueError('Origen debe ser measured o synthetic.')
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or any(k not in reader.fieldnames for k in REQUIRED):
            raise ValueError('Faltan columnas obligatorias: ' + ', '.join(REQUIRED))
        rows, previous = [], -1.0
        for number, row in enumerate(reader, 2):
            try:
                values = {k: float(row[k]) for k in REQUIRED[:5]}
                for k in OPTIONAL:
                    if row.get(k, '').strip():
                        values[k] = float(row[k])
                if not all(math.isfinite(v) for v in values.values()):
                    raise ValueError('valor no finito')
                if values['acquisition_time'] < 0 or values['acquisition_time'] <= previous:
                    raise ValueError('tiempos deben ser no negativos y estrictamente crecientes')
                for k in REQUIRED[5:]:
                    values[k] = row[k].strip()
                    if not values[k]:
                        raise ValueError('sensor sin tipo o ubicación')
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError(f'Fila {number}: {exc}') from exc
            previous = values['acquisition_time']
            row_origin = row.get('origin', '').strip() or origin
            if row_origin not in ('measured', 'synthetic') or (origin and row_origin != origin):
                raise ValueError(f'Fila {number}: origen measured/synthetic obligatorio y coherente.')
            values['origin'] = row_origin
            rows.append(values)
    if not rows:
        raise ValueError('El ensayo está vacío.')
    return rows
