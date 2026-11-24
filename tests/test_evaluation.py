import unittest
from motorlab.evaluation import evaluate_episodes


def interval(identifier, signal, start, end, **extra):
    return {'id': identifier, 'signal': signal, 'start_time': start, 'end_time': end, **extra}


class EvaluationTests(unittest.TestCase):
    def test_detection_miss_false_alert_and_delay(self):
        episodes = [
            interval('episode-current', 'current', 3, 4.5),
            interval('episode-temperature', 'temperature', 3.5, 5),
            interval('episode-extra', 'current', 7, 8),
        ]
        labels = [
            interval('expected-current', 'current', 2, 4),
            interval('expected-temperature', 'temperature', 3, 5),
            interval('expected-residual', 'voltage_residual', 8, 9),
        ]
        result = evaluate_episodes(episodes, labels)
        self.assertEqual(result['detection_count'], 2)
        self.assertEqual(result['missed_count'], 1)
        self.assertEqual(result['false_alert_count'], 1)
        self.assertEqual(result['missed'], ['expected-residual'])
        self.assertEqual(result['false_alerts'], ['episode-extra'])
        self.assertEqual(result['mean_delay_s'], .75)
        self.assertEqual(result, evaluate_episodes(episodes, labels))

    def test_one_to_one_matching(self):
        episodes = [interval('e1', 'current', 2, 3), interval('e2', 'current', 2.5, 3.5)]
        labels = [interval('l1', 'current', 2, 3)]
        result = evaluate_episodes(episodes, labels)
        self.assertEqual(result['detection_count'], 1)
        self.assertEqual(result['false_alert_count'], 1)

    def test_maximum_cardinality_matching_with_overlapping_labels(self):
        episodes = [interval('e1', 'current', 5, 5.1), interval('e2', 'current', 8, 8.1)]
        labels = [interval('A', 'current', 0, 10), interval('B', 'current', 5, 6)]
        result = evaluate_episodes(episodes, labels)
        self.assertEqual(result['detection_count'], 2)
        self.assertEqual(result['missed_count'], 0)
        self.assertEqual(result['false_alert_count'], 0)
        self.assertEqual({item['label_id']: item['episode_id'] for item in result['detections']},
                         {'A': 'e2', 'B': 'e1'})

    def test_non_persistent_label_is_not_an_omission_but_alert_is_false(self):
        label = interval('peak', 'current', 2, 2.5, expect_alert=False)
        self.assertEqual(evaluate_episodes([], [label])['missed_count'], 0)
        result = evaluate_episodes([interval('episode', 'current', 2, 2.5)], [label])
        self.assertEqual(result['detection_count'], 0)
        self.assertEqual(result['false_alert_count'], 1)
        self.assertEqual(result['false_alerts'], ['episode'])

    def test_invalid_or_duplicate_intervals(self):
        with self.assertRaisesRegex(ValueError, 'únicos'):
            evaluate_episodes([interval('same', 'current', 0, 1), interval('same', 'current', 1, 2)], [])
        with self.assertRaisesRegex(ValueError, 'inválido'):
            evaluate_episodes([interval('e', 'current', 2, 1)], [])
        with self.assertRaisesRegex(ValueError, 'Faltan'):
            evaluate_episodes([], [{'id': 'incomplete'}])
        with self.assertRaisesRegex(ValueError, 'booleano'):
            evaluate_episodes([], [interval('l', 'current', 0, 1, expect_alert='no')])


if __name__ == '__main__':
    unittest.main()
