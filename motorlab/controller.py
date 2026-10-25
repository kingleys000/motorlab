"""Reloj de simulación, experimentos y distribución de telemetría a ambas ventanas."""
from collections import deque
import time

from PySide6.QtCore import QObject, QTimer, Signal

from .model import Motor, Inputs, SCENARIOS


class Controller(QObject):
    sample = Signal(dict)
    changed = Signal()
    reset_done = Signal()
    event = Signal(str)
    failure = Signal(str)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.motor = Motor()
        self.session = store.new_session()
        self.history = deque(maxlen=6000)  # 10 minutos a 10 Hz; sesiones completas en disco.
        self.running = False
        self.speed = 1.0
        self.demo_start = None
        self.demo_stage = -1
        self.scenario = 'Marcha nominal'
        self.accumulator = 0.0
        self.steps = 0
        self.previous = time.monotonic()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def toggle(self):
        self.running = not self.running
        self.previous = time.monotonic()
        self.event.emit('Simulación iniciada' if self.running else 'Simulación en pausa')
        self.changed.emit()

    def reset(self):
        self.running = False
        self.demo_start = None
        self.motor.reset()
        self.history.clear()
        self.session = self.store.new_session()
        self.accumulator = 0
        self.steps = 0
        self.reset_done.emit()
        self.changed.emit()
        self.event.emit('Nueva sesión · la anterior permanece en el historial')

    def set_scenario(self, name, manual=True):
        self.scenario = name
        self.motor.inputs = Inputs(*SCENARIOS[name])
        if manual:
            self.demo_start = None
        self.event.emit(name)
        self.changed.emit()

    def set_input(self, name, value):
        setattr(self.motor.inputs, name, value)
        self.scenario = 'Personalizado'
        self.demo_start = None
        self.changed.emit()

    def start_demo(self):
        self.reset()
        self.demo_start = 0.0
        self.demo_stage = -1
        self.running = True
        self.speed = 5.0
        self.previous = time.monotonic()
        self.event.emit('Experimento guiado · 90 segundos simulados a 5×')
        self.changed.emit()

    def update_demo(self):
        if self.demo_start is None:
            return
        t = self.motor.time - self.demo_start
        stage = 0 if t < 15 else 1 if t < 45 else 2 if t < 75 else 3
        if stage != self.demo_stage:
            self.demo_stage = stage
            self.set_scenario(list(SCENARIOS)[stage], manual=False)
        if t >= 90:
            self.demo_start = None
            self.running = False
            self.event.emit('Experimento completo · explora las gráficas o exporta los datos')
            self.changed.emit()

    def tick(self):
        now = time.monotonic()
        elapsed, self.previous = min(now - self.previous, 0.2), now
        if not self.running:
            return
        # Si el equipo se retrasa, se sacrifica velocidad de reproducción, nunca el paso físico.
        self.accumulator += elapsed * self.speed
        while self.accumulator >= 0.001 and self.running:
            self.update_demo()
            if not self.running:
                break
            self.motor.step()
            self.steps += 1
            self.accumulator -= 0.001
            if self.steps % 100 == 0:
                point = self.motor.snapshot()
                try:
                    self.store.append(self.session, point)
                except Exception as exc:
                    self.running = False
                    self.failure.emit('No se pudo guardar la muestra local. Se pausó la simulación: ' + str(exc))
                    self.changed.emit()
                    break
                self.history.append(point)
                self.sample.emit(point)
