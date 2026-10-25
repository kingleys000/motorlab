import math
import unittest

from motorlab.model import Motor, Parameters


def advance(motor, seconds, step=.001):
    for _ in range(round(seconds/step)):
        motor.step(step)


class PhysicsTests(unittest.TestCase):
    def test_unpowered_motor_remains_at_equilibrium(self):
        motor = Motor()
        motor.inputs.voltage = 0
        advance(motor, 1)
        self.assertEqual((motor.current, motor.omega, motor.temperature), (0, 0, 25))

    def test_matches_analytical_mechanical_equilibrium(self):
        motor = Motor(Parameters(copper_alpha=0))
        advance(motor, 15)
        p, u = motor.p, motor.inputs
        expected = (p.torque_constant*u.voltage-p.resistance*u.load) / (p.torque_constant**2+p.resistance*p.friction)
        self.assertAlmostEqual(motor.omega, expected, places=6)

    def test_load_slows_rotor_and_increases_current(self):
        motor = Motor()
        advance(motor, 10)
        speed, current = motor.omega, motor.current
        motor.inputs.load = .65
        advance(motor, 10)
        self.assertLess(motor.omega, speed)
        self.assertGreater(motor.current, current)
        self.assertGreater(motor.temperature, 25)

    def test_total_energy_balance(self):
        motor = Motor()
        i, omega, temperature = 3, 120, 48
        di, dw, dT = motor.derivative((i, omega, temperature))
        p, u = motor.p, motor.inputs
        stored_derivative = p.inductance*i*di + p.inertia*omega*dw + p.thermal_capacity*dT
        external = u.voltage*i - u.load*math.tanh(omega/2)*omega - u.cooling*(temperature-p.ambient)
        self.assertAlmostEqual(stored_derivative, external, places=10)

    def test_rk4_matches_smaller_step_at_startup(self):
        coarse, fine = Motor(), Motor()
        advance(coarse, .02, .001)
        advance(fine, .02, .00025)
        self.assertAlmostEqual(coarse.current, fine.current, places=4)
        self.assertAlmostEqual(coarse.omega, fine.omega, places=4)

    def test_stronger_cooling_reduces_temperature(self):
        motor = Motor()
        motor.inputs.voltage = 0
        state = (0, 0, 60)
        slow = motor.derivative(state)[2]
        motor.inputs.cooling = 2
        self.assertLess(motor.derivative(state)[2], slow)


if __name__ == '__main__':
    unittest.main()
