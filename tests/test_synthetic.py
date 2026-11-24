import json
from pathlib import Path
import tempfile
import unittest
from motorlab.calibration import Calibration
from motorlab.diagnostics import Limits, detect_episodes
from motorlab.evaluation import evaluate_episodes
from motorlab.experiments import read_experiment
from motorlab.model import Parameters
from motorlab.synthetic import ANOMALY_KINDS, anomaly_experiment, healthy_experiment, modeled_voltage, write_corpus

CALIBRATION = Calibration(Parameters(resistance=1.7, torque_constant=.09), 0, 0, 3, 3, 'synthetic')


def predictions(rows):
    return [modeled_voltage(row['current'], row['rpm'], row['temperature']) for row in rows]


class SyntheticTests(unittest.TestCase):
    def test_reproducible_and_labels_are_separate(self):
        first = healthy_experiment(seed=42)
        self.assertEqual(first, healthy_experiment(seed=42))
        self.assertNotEqual(first, healthy_experiment(seed=43))
        for kind in ANOMALY_KINDS:
            with self.subTest(kind=kind):
                rows, labels = anomaly_experiment(kind, seed=42)
                self.assertEqual((rows, labels), anomaly_experiment(kind, seed=42))
                self.assertTrue(labels)
                self.assertTrue(all('label' not in row and 'labels' not in row for row in rows))
                self.assertTrue(all(label['signal'] in ('current', 'temperature', 'voltage_residual')
                                    for label in labels))

    def test_persistent_anomaly_and_brief_peak_evaluation(self):
        rows, labels = anomaly_experiment('overcurrent', seed=42)
        limits = Limits(current_max=3, persistence_s=1, clear_s=.5)
        result = evaluate_episodes(detect_episodes(rows, limits), labels)
        self.assertEqual(result['detection_count'], 1)
        self.assertEqual(result['missed_count'], 0)
        self.assertEqual(result['false_alert_count'], 0)
        self.assertEqual(result['detections'][0]['delay_s'], 1)

        rows, labels = anomaly_experiment('brief_peak', seed=42)
        result = evaluate_episodes(detect_episodes(rows, limits), labels)
        self.assertEqual(result['detection_count'], 0)
        self.assertEqual(result['missed_count'], 0)
        self.assertEqual(result['false_alert_count'], 0)
        self.assertEqual(result['not_expected'], [labels[0]['id']])
        brief_without_persistence = evaluate_episodes(
            detect_episodes(rows, Limits(current_max=3, persistence_s=0, clear_s=0)), labels)
        self.assertEqual(brief_without_persistence['detection_count'], 0)
        self.assertEqual(brief_without_persistence['false_alert_count'], 1)

    def test_combined_and_residual(self):
        rows, labels = anomaly_experiment('combined', seed=42)
        limits = Limits(current_max=3, temperature_max=40, voltage_residual_max=.5,
                        persistence_s=1, clear_s=.5)
        result = evaluate_episodes(detect_episodes(
            rows, limits, predicted_voltages=predictions(rows), steady_state=True, calibration=CALIBRATION), labels)
        self.assertEqual(result['detection_count'], 2)
        self.assertEqual(result['false_alert_count'], 0)

        rows, labels = anomaly_experiment('voltage_residual', seed=42)
        limits = Limits(voltage_residual_max=.5, persistence_s=1, clear_s=.5)
        episodes = detect_episodes(rows, limits, predicted_voltages=predictions(rows), steady_state=True, calibration=CALIBRATION)
        self.assertEqual(evaluate_episodes(episodes, labels)['detection_count'], 1)

    def test_corpus_is_importable_and_labels_stay_in_json(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_corpus(directory, seed=42)
            self.assertEqual(len(manifest), 8)
            for name, item in manifest.items():
                rows = read_experiment(item['data'])
                self.assertTrue(rows)
                header = Path(item['data']).read_text(encoding='utf-8').splitlines()[0]
                self.assertNotIn('label', header)
                if item['labels'] is not None:
                    labels = json.loads(Path(item['labels']).read_text(encoding='utf-8'))
                    self.assertEqual(labels == [], name == 'evaluacion_saludable')
            healthy = manifest['evaluacion_saludable']
            result = evaluate_episodes(detect_episodes(
                read_experiment(healthy['data']), Limits(current_max=3, temperature_max=40)), [])
            self.assertEqual(result['false_alert_count'], 0)

    def test_invalid_generation_arguments(self):
        with self.assertRaisesRegex(ValueError, 'desconocido'):
            anomaly_experiment('unknown')
        with self.assertRaisesRegex(ValueError, 'paso'):
            healthy_experiment(step_s=0)
        with self.assertRaisesRegex(ValueError, 'mínima'):
            anomaly_experiment('combined', duration_s=5)


if __name__ == '__main__':
    unittest.main()
