"""Identificación eléctrica estacionaria, sin ajustar parámetros no observables."""
from dataclasses import dataclass, replace
import math
import numpy as np
from .model import Parameters

@dataclass(frozen=True)
class Calibration:
    parameters: Parameters
    training_rmse_v: float
    validation_rmse_v: float
    training_count: int
    validation_count: int
    origin: str
    fixed: tuple = ('inductance', 'inertia', 'friction', 'thermal_capacity', 'ambient', 'copper_alpha')
    adjusted: tuple = ('resistance', 'torque_constant')


def _matrix(rows, p):
    if len(rows) < 3:
        raise ValueError('Se requieren al menos tres muestras por ensayo.')
    # El modelo térmico representa bobinado; carcasa no corrige resistencia.
    if any(r.get('sensor_location', '').strip().lower() not in ('bobinado', 'winding') for r in rows):
        raise ValueError('La corrección térmica requiere temperatura de bobinado; carcasa no es equivalente.')
    x = np.array([[r['current'] * (1 + p.copper_alpha * (r['temperature'] - 25)),
                   r['rpm'] * math.tau / 60] for r in rows], dtype=float)
    y = np.array([r['voltage'] for r in rows], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Las muestras deben ser finitas.')
    return x, y


def calibrate(training, validation, parameters=Parameters(), *, steady_state=False):
    """Ajusta R y K con V=RI+Kω; el usuario declara régimen estacionario saludable.

    Los dos ensayos deben ser independientes; no se usa la temperatura de carcasa.
    No infiere inductancia, carga, fricción ni validación física del motor.
    """
    if not steady_state:
        raise ValueError('Declare que ambos ensayos son saludables y estacionarios.')
    if training is validation or training == validation:
        raise ValueError('Ajuste y validación requieren ensayos distintos.')
    origins = {r.get('origin') for r in list(training) + list(validation)}
    if len(origins) != 1 or not origins <= {'measured', 'synthetic'}:
        raise ValueError('Los ensayos deben tener un mismo origen explícito.')
    x, y = _matrix(training, parameters)
    xv, yv = _matrix(validation, parameters)
    scale = np.linalg.norm(x, axis=0)
    if np.any(scale < 1e-10) or np.linalg.matrix_rank(x / scale, tol=1e-3) < 2 or np.linalg.cond(x / scale) > 1000:
        raise ValueError('Ensayo insuficiente: corriente y velocidad no identifican R y K por separado.')
    fit = np.linalg.lstsq(x, y, rcond=None)[0]
    if not (1e-6 <= fit[0] <= 1e4 and 1e-7 <= fit[1] <= 1e3):
        raise ValueError('Ajuste fuera de cotas físicas; revise los ensayos.')
    rmse = lambda a: float(np.sqrt(np.mean(a*a)))
    return Calibration(replace(parameters, resistance=float(fit[0]), torque_constant=float(fit[1])),
                       rmse(y-x@fit), rmse(yv-xv@fit), len(y), len(yv), origins.pop())


def compare(rows, parameters):
    x, y = _matrix(rows, parameters)
    predictions = x @ np.array([parameters.resistance, parameters.torque_constant])
    return [{'acquisition_time': row['acquisition_time'], 'observed_voltage': float(observed),
             'predicted_voltage': float(predicted), 'residual_voltage': float(observed-predicted)}
            for row, observed, predicted in zip(rows, y, predictions)]
