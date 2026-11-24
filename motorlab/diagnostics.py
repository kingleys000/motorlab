"""Alertas y episodios reproducibles con límites y tiempos explícitos."""
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
import math

ANALYSIS_VERSION = 'diagnostics-v1'
HYPOTHESES = {
    'current': 'Posible sobrecarga; requiere comprobación.',
    'temperature': 'Posible refrigeración insuficiente o sobrecarga; requiere comprobación.',
    'voltage_residual': 'Desviación del modelo; posibles cambios o error de sensor.',
}
UNITS = {
    'current': 'A', 'sensor_current': 'A',
    'temperature': '°C', 'sensor_temperature': '°C',
    'voltage_residual': 'V', 'sensor_voltage': 'V',
}


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class Limits:
    current_max: float | None = None
    temperature_max: float | None = None
    voltage_residual_max: float | None = None
    persistence_s: float = 1.0
    clear_s: float = 1.0

    def __post_init__(self):
        for v in (self.current_max, self.temperature_max, self.voltage_residual_max):
            if v is not None and (not math.isfinite(v) or v <= 0):
                raise ValueError('Los límites deben ser positivos y finitos.')
        if not all(math.isfinite(x) and x >= 0 for x in (self.persistence_s, self.clear_s)):
            raise ValueError('Los tiempos deben ser finitos y no negativos.')


class Detector:
    def __init__(self, limits):
        self.limits = limits
        self.last_time = None
        self.since = {}
        self.clear_since = {}
        self.active = set()

    def update(self, sample, predicted_voltage=None):
        if not isinstance(sample, Mapping):
            raise ValueError('La muestra debe ser un mapeo de señales.')
        t = sample.get('acquisition_time')
        if not _finite_number(t) or t < 0 or (self.last_time is not None and t <= self.last_time):
            raise ValueError('El tiempo de adquisición debe ser finito, no negativo y creciente.')
        self.last_time = t
        checks = {}
        for key, limit in (('current', self.limits.current_max), ('temperature', self.limits.temperature_max)):
            value = sample.get(key)
            valid = _finite_number(value)
            checks['sensor_' + key] = not valid
            if valid and limit is not None:
                checks[key] = abs(value) > limit if key == 'current' else value > limit
        if predicted_voltage is not None and self.limits.voltage_residual_max is not None:
            voltage = sample.get('voltage')
            valid = _finite_number(voltage) and _finite_number(predicted_voltage)
            checks['sensor_voltage'] = not valid
            if valid:
                checks['voltage_residual'] = abs(voltage - predicted_voltage) > self.limits.voltage_residual_max
        for name in set(checks) | self.active | set(self.since):
            # No se limpia una alarma por falta de una medición utilizable.
            if name not in checks:
                self.since.pop(name, None)
                self.clear_since.pop(name, None)
                continue
            if checks[name]:
                self.clear_since.pop(name, None)
                self.since.setdefault(name, t)
                if t - self.since[name] >= self.limits.persistence_s:
                    self.active.add(name)
            else:
                self.since.pop(name, None)
                self.clear_since.setdefault(name, t)
                if t - self.clear_since[name] >= self.limits.clear_s:
                    self.active.discard(name)
        return [{'id': name, 'acquisition_time': t,
                 'hypothesis': HYPOTHESES.get(name, 'Sensor ausente o inválido.'),
                 'kind': 'observacion'} for name in sorted(self.active)]


def _limit_for(signal, limits):
    if signal == 'current':
        return limits.current_max
    if signal == 'temperature':
        return limits.temperature_max
    if signal == 'voltage_residual':
        return limits.voltage_residual_max
    return None


def _episode_value(sample, signal, predicted_voltage):
    if signal == 'voltage_residual':
        voltage = sample.get('voltage')
        if _finite_number(voltage) and _finite_number(predicted_voltage):
            return abs(voltage - predicted_voltage)
        return None
    key = signal.removeprefix('sensor_')
    value = sample.get(key)
    return float(value) if _finite_number(value) else None


def _update_peak(episode, value):
    if value is None:
        return
    previous = episode['value']
    if previous is None:
        episode['value'] = value
    elif episode['signal'] == 'temperature' and value > previous:
        episode['value'] = value
    elif episode['signal'] != 'temperature' and abs(value) > abs(previous):
        episode['value'] = value


def _validate_residual_calibration(samples, predictions, calibration, origin, steady_state):
    from .calibration import Calibration
    if not steady_state:
        raise ValueError('El residual requiere una calibración compatible y régimen estacionario declarado.')
    if not isinstance(calibration, Calibration):
        raise ValueError('El residual requiere un objeto Calibration compatible.')
    parameters = calibration.parameters
    for sample, predicted in zip(samples, predictions):
        row_origin = origin if origin is not None else sample.get('origin')
        if row_origin != calibration.origin:
            raise ValueError('El origen del ensayo no coincide con la calibración.')
        if sample.get('sensor_location', '').strip().lower() not in ('bobinado', 'winding'):
            raise ValueError('El residual requiere temperatura de bobinado compatible con la calibración.')
        if predicted is None:
            continue
        try:
            expected = (parameters.resistance * sample['current']
                        * (1 + parameters.copper_alpha * (sample['temperature'] - 25))
                        + parameters.torque_constant * math.tau * sample['rpm'] / 60)
        except (KeyError, TypeError) as exc:
            raise ValueError('Faltan señales para comprobar las predicciones calibradas.') from exc
        if not _finite_number(predicted) or not _finite_number(expected) or not math.isclose(
                predicted, expected, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError('Las predicciones no corresponden a la calibración y a las muestras.')


def detect_episodes(rows, limits, *, predicted_voltages=None, origin=None,
                    steady_state=False, calibration=None, analysis_version=ANALYSIS_VERSION):
    """Convierte muestras ordenadas en episodios únicos, incluidos los activos al final."""
    if origin is not None and origin not in ('measured', 'synthetic'):
        raise ValueError('El origen debe ser measured o synthetic.')
    if not isinstance(analysis_version, str) or not analysis_version.strip():
        raise ValueError('La versión del análisis debe ser texto no vacío.')
    samples = list(rows)
    if not samples:
        raise ValueError('El ensayo está vacío.')
    predictions = [None] * len(samples) if predicted_voltages is None else list(predicted_voltages)
    if len(predictions) != len(samples):
        raise ValueError('Debe haber una predicción por muestra.')
    if limits.voltage_residual_max is not None and any(p is not None for p in predictions):
        _validate_residual_calibration(samples, predictions, calibration, origin, steady_state)
    try:
        content = json.dumps({
            'samples': [dict(sample) for sample in samples],
            'limits': asdict(limits),
            'predicted_voltages': predictions,
            'origin': origin,
            'steady_state': steady_state,
            'calibration': asdict(calibration) if calibration is not None else None,
            'analysis_version': analysis_version,
        }, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('Las muestras, predicciones y calibración deben ser serializables.') from exc
    fingerprint = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    detector = Detector(limits)
    open_episodes = {}
    episodes = []
    last_time = None
    for sample, predicted_voltage in zip(samples, predictions):
        previously_open = set(open_episodes)
        active = {alert['id'] for alert in detector.update(sample, predicted_voltage)}
        t = sample['acquisition_time']
        row_origin = origin if origin is not None else sample.get('origin')
        if row_origin not in ('measured', 'synthetic'):
            raise ValueError('Cada muestra debe declarar origen measured o synthetic.')
        if origin is not None and sample.get('origin', origin) != origin:
            raise ValueError('El origen de una muestra no coincide con el ensayo.')
        last_time = t

        for signal in sorted(active - previously_open):
            value = _episode_value(sample, signal, predicted_voltage)
            open_episodes[signal] = {
                'id': f'episode-{fingerprint}-{len(open_episodes) + len(episodes) + 1:06d}-{signal}',
                'signal': signal,
                'value': value,
                'limit': _limit_for(signal, limits),
                'unit': UNITS[signal],
                'start_time': t,
                'end_time': None,
                'interval_s': [t, None],
                'persistence_start_time': detector.since.get(signal, t),
                'acquisition_time': t,
                'origin': row_origin,
                'analysis_version': analysis_version,
                'hypothesis': HYPOTHESES.get(signal, 'Sensor ausente o inválido.'),
                'kind': 'observacion',
            }
        for signal in sorted(active):
            _update_peak(open_episodes[signal], _episode_value(sample, signal, predicted_voltage))
        for signal in sorted(previously_open - active):
            episode = open_episodes.pop(signal)
            episode['end_time'] = t
            episode['interval_s'] = [episode['start_time'], t]
            episodes.append(episode)

    for signal in sorted(open_episodes):
        episode = open_episodes[signal]
        episode['end_time'] = last_time
        episode['interval_s'] = [episode['start_time'], last_time]
        episodes.append(episode)
    return sorted(episodes, key=lambda episode: (episode['start_time'], episode['id']))
