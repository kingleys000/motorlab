import unittest
from motorlab.calibration import Calibration
from motorlab.diagnostics import Detector, Limits, detect_episodes
from motorlab.model import Parameters

CALIBRATION = Calibration(Parameters(resistance=1.7, torque_constant=.09), 0, 0, 3, 3, 'synthetic')


def sample(t, current=1.0, temperature=25.0, voltage=12.0):
    return {
        'acquisition_time': t,
        'current': current,
        'temperature': temperature,
        'voltage': voltage,
        'rpm': 0.0,
        'sensor_location': 'bobinado',
        'origin': 'synthetic',
    }


class EpisodeTests(unittest.TestCase):
    def test_repeated_episodes_peak_interval_and_reproducible_ids(self):
        rows = [
            sample(0), sample(.5, 4), sample(1), sample(2, 4), sample(3, 4),
            sample(3.5, 5), sample(4), sample(5), sample(6, 4), sample(7, 4),
        ]
        limits = Limits(current_max=3, persistence_s=1, clear_s=1)
        episodes = detect_episodes(rows, limits)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0]['signal'], 'current')
        self.assertEqual(episodes[0]['value'], 5)
        self.assertEqual(episodes[0]['limit'], 3)
        self.assertEqual(episodes[0]['unit'], 'A')
        self.assertEqual(episodes[0]['interval_s'], [3, 5])
        self.assertEqual(episodes[1]['interval_s'], [7, 7])
        self.assertEqual(episodes[0]['origin'], 'synthetic')
        self.assertEqual(episodes[0]['analysis_version'], 'diagnostics-v1')
        self.assertNotEqual(episodes[0]['id'], episodes[1]['id'])
        self.assertEqual([item['id'] for item in episodes],
                         [item['id'] for item in detect_episodes(rows, limits)])
        changed = detect_episodes(rows, Limits(current_max=3.5, persistence_s=1, clear_s=1))
        self.assertNotEqual(episodes[0]['id'], changed[0]['id'])

    def test_residual_requires_stationary_compatible_calibration(self):
        rows = [sample(0, voltage=2.7), sample(1, voltage=2.7), sample(2, voltage=2.7)]
        limits = Limits(voltage_residual_max=.5, persistence_s=1, clear_s=0)
        with self.assertRaisesRegex(ValueError, 'estacionario'):
            detect_episodes(rows, limits, predicted_voltages=[1.7] * 3, calibration=CALIBRATION)
        with self.assertRaisesRegex(ValueError, 'Calibration'):
            detect_episodes(rows, limits, predicted_voltages=[1.7] * 3, steady_state=True)
        with self.assertRaisesRegex(ValueError, 'no corresponden'):
            detect_episodes(rows, limits, predicted_voltages=[10] * 3,
                            steady_state=True, calibration=CALIBRATION)
        episodes = detect_episodes(rows, limits, predicted_voltages=[1.7] * 3,
                                   steady_state=True, calibration=CALIBRATION)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]['signal'], 'voltage_residual')
        self.assertAlmostEqual(episodes[0]['value'], 1)
        self.assertEqual(episodes[0]['unit'], 'V')

    def test_invalid_inputs_are_clear(self):
        with self.assertRaisesRegex(ValueError, 'vacío'):
            detect_episodes([], Limits())
        with self.assertRaisesRegex(ValueError, 'predicción'):
            detect_episodes([sample(0)], Limits(), predicted_voltages=[])
        with self.assertRaisesRegex(ValueError, 'origen'):
            detect_episodes([{**sample(0), 'origin': ''}], Limits())
        with self.assertRaisesRegex(ValueError, 'creciente'):
            Detector(Limits()).update({'acquisition_time': float('nan')})
        with self.assertRaisesRegex(ValueError, 'mapeo'):
            Detector(Limits()).update(None)
        with self.assertRaisesRegex(ValueError, 'versión'):
            detect_episodes([sample(0)], Limits(), analysis_version='')


if __name__ == '__main__':
    unittest.main()
