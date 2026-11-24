"""Modelo concentrado electromecánico y térmico. Todas las unidades son SI.

No depende de la interfaz ni de la base de datos: se puede estudiar por separado.
El integrador RK4 usa pasos de 1 ms, independientes de la frecuencia de dibujo.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Parameters:
    resistance: float = 1.2       # ohm, a 25 °C
    inductance: float = 0.012     # H
    torque_constant: float = 0.08 # N m/A; también V s/rad en unidades SI
    inertia: float = 0.0025       # kg m²
    friction: float = 0.0003      # N m s/rad
    thermal_capacity: float = 35 # J/K
    ambient: float = 25.0        # °C
    copper_alpha: float = 0.00393 # 1/K


@dataclass
class Inputs:
    voltage: float = 18.0        # V
    load: float = 0.06           # N m, carga resistente suave
    cooling: float = 0.55        # W/K


class Motor:
    def __init__(self, parameters=None):
        self.p = parameters or Parameters()
        self.inputs = Inputs()
        self.reset()

    def reset(self):
        self.time = 0.0
        self.current = 0.0
        self.omega = 0.0
        self.temperature = self.p.ambient
        self.angle = 0.0

    def resistance(self, temperature):
        return self.p.resistance * (1 + self.p.copper_alpha * (temperature - 25))

    def derivative(self, state):
        current, omega, temperature = state
        p, u = self.p, self.inputs
        resistance = self.resistance(temperature)
        # tanh evita la discontinuidad del signo en el arranque y parada.
        load_torque = u.load * math.tanh(omega / 2.0)
        return (
            (u.voltage - resistance * current - p.torque_constant * omega) / p.inductance,
            (p.torque_constant * current - p.friction * omega - load_torque) / p.inertia,
            (current * current * resistance + p.friction * omega * omega
             - u.cooling * (temperature - p.ambient)) / p.thermal_capacity,
        )

    def step(self, dt=0.001):
        """Un paso de Runge–Kutta de cuarto orden."""
        if not 0 < dt <= 0.00100001:
            raise ValueError('El paso debe estar entre 0 y 0.001 segundos.')
        # Resuelve la escala eléctrica rápida con subpasos, conservando el reloj externo.
        resistance = abs(self.resistance(self.temperature))
        if self.p.inductance <= 0 or self.p.inertia <= 0 or self.p.thermal_capacity <= 0:
            raise ValueError('Inductancia, inercia y capacidad térmica deben ser positivas.')
        rate = resistance / self.p.inductance + abs(self.p.torque_constant) / math.sqrt(self.p.inductance * self.p.inertia) + abs(self.p.friction) / self.p.inertia
        count = max(1, math.ceil(dt * rate / 0.5))
        if count > 10000:
            raise ValueError('Parámetros demasiado rígidos para el integrador.')
        h = dt / count
        for _ in range(count):
            self._rk4(h)

    def _rk4(self, dt):
        y = (self.current, self.omega, self.temperature)
        k1 = self.derivative(y)
        k2 = self.derivative(tuple(a + dt * b / 2 for a, b in zip(y, k1)))
        k3 = self.derivative(tuple(a + dt * b / 2 for a, b in zip(y, k2)))
        k4 = self.derivative(tuple(a + dt * b for a, b in zip(y, k3)))
        self.current, self.omega, self.temperature = (
            a + dt * (b + 2*c + 2*d + e) / 6
            for a, b, c, d, e in zip(y, k1, k2, k3, k4)
        )
        self.time += dt
        self.angle = (self.angle + self.omega * dt) % math.tau

    def snapshot(self):
        p, u = self.p, self.inputs
        power_in = u.voltage * self.current
        useful_power = u.load * math.tanh(self.omega / 2) * self.omega
        return {
            'sim_time': self.time,
            'rpm': self.omega * 60 / math.tau,
            'current': self.current,
            'temperature': self.temperature,
            'voltage': u.voltage,
            'load': u.load,
            'cooling': u.cooling,
            'torque': p.torque_constant * self.current,
            'power_in': power_in,
            'power_out': useful_power,
            # El cociente sólo es una eficiencia física en régimen estacionario.
            'power_ratio': useful_power / power_in * 100 if power_in > 0.01 else 0.0,
        }


SCENARIOS = {
    'Marcha nominal': (18.0, 0.06, 0.55),
    'Carga elevada': (18.0, 0.65, 0.55),
    'Refrigeración reducida': (24.0, 0.50, 0.15),
    'Desaceleración eléctrica': (0.0, 0.06, 0.55),
}
