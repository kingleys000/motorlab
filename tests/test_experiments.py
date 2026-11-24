import tempfile
import unittest
from pathlib import Path
from motorlab.experiments import read_experiment

HEADER = 'acquisition_time,voltage,current,rpm,temperature,sensor_type,sensor_location,load,ambient\n'

class ExperimentTests(unittest.TestCase):
    def test_csv_units_origin_and_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ensayo.csv'
            path.write_text(HEADER + '0,12,1,300,25,termopar,carcasa,,\n1,12,2,400,26,termopar,carcasa,0.1,24\n')
            rows = read_experiment(path, origin='synthetic')
            self.assertEqual(rows[0]['origin'], 'synthetic')
            self.assertNotIn('load', rows[0])
            self.assertEqual(rows[1]['load'], 0.1)
            self.assertEqual(rows[0]['sensor_location'], 'carcasa')

    def test_invalid_rows(self):
        examples = ['0,nan,1,2,3,tipo,lugar,,\n', '-1,1,1,2,3,tipo,lugar,,\n', '0,1,1,2,3,tipo,lugar,,\n0,1,1,2,3,tipo,lugar,,\n', '0,1,1,2,3,,lugar,,\n']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.csv'
            for rows in examples:
                with self.subTest(rows=rows):
                    path.write_text(HEADER + rows)
                    with self.assertRaises(ValueError):
                        read_experiment(path)
