import math
import tempfile
import unittest
from pathlib import Path
from motorlab.calibration import calibrate, compare
from motorlab.diagnostics import Detector, Limits
from motorlab.experiments import read_experiment
from motorlab.model import Motor, Parameters


def rows(points):
    return [{'acquisition_time': float(n), 'current': i, 'rpm': omega*60/math.tau,
             'temperature': 25., 'sensor_location': 'bobinado', 'sensor_type': 'synthetic',
             'origin': 'synthetic', 'voltage': 1.7*i + .09*omega} for n, (i, omega) in enumerate(points)]

class TwinTests(unittest.TestCase):
    def test_fit_and_independent_validation(self):
        train = rows([(1, 20), (2, 60), (3, 40), (4, 80)])
        valid = rows([(1.5, 35), (2.5, 65), (4.5, 45)])
        result = calibrate(train, valid, steady_state=True)
        self.assertAlmostEqual(result.parameters.resistance, 1.7)
        self.assertAlmostEqual(result.parameters.torque_constant, .09)
        self.assertLess(result.validation_rmse_v, 1e-10)
        self.assertLess(abs(compare(valid, result.parameters)[0]['residual_voltage']), 1e-10)
        with self.assertRaises(ValueError): calibrate(train, train, steady_state=True)
        with self.assertRaises(ValueError): calibrate(train, valid)
        with self.assertRaises(ValueError): calibrate(rows([(1,10),(2,20),(3,30)]), valid, steady_state=True)
        train[0]['sensor_location'] = 'carcasa'
        with self.assertRaises(ValueError): calibrate(train, valid, steady_state=True)

    def test_stiff_integrator_converges(self):
        p = Parameters(inductance=.00005)
        coarse, fine = Motor(p), Motor(p)
        for _ in range(20): coarse.step(.001)
        for _ in range(200): fine.step(.0001)
        self.assertAlmostEqual(coarse.current, fine.current, places=3)
        self.assertAlmostEqual(coarse.omega, fine.omega, places=3)

    def test_persistence_and_invalid_sensor(self):
        detector = Detector(Limits(current_max=3, persistence_s=1, clear_s=1))
        def run(t, value): return {a['id'] for a in detector.update({'acquisition_time': t, 'current': value, 'temperature': 25})}
        self.assertEqual(run(0, 1), set())
        self.assertEqual(run(.5, 4), set())
        self.assertEqual(run(1, 1), set())
        self.assertEqual(run(2, 4), set())
        self.assertIn('current', run(3, 4))
        self.assertIn('current', run(3.5, float('nan')))
        self.assertIn('sensor_current', run(4.5, float('nan')))
        self.assertIn('current', run(5, 1))
        self.assertNotIn('current', run(6, 1))

    def test_origin_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'x.csv'
            p.write_text('acquisition_time,voltage,current,rpm,temperature,sensor_type,sensor_location,origin\n0,1,1,1,25,t,bobinado,synthetic\n')
            self.assertEqual(read_experiment(p)[0]['origin'], 'synthetic')
            p.write_text(p.read_text().replace('synthetic',''))
            with self.assertRaises(ValueError): read_experiment(p)
