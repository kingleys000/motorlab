import json
import io
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from concurrent.futures import Future
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from motorlab.controller import Controller
from motorlab.storage import SessionStore, Settings, SyncWorker
from motorlab.theme import ThemeManager
from motorlab.ui import DashboardWindow, STYLE

class DiagnosticViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.app.motorlab_theme = ThemeManager(STYLE, Path(self.temp.name)/'theme.json')
        self.store = SessionStore(Path(self.temp.name)/'db.sqlite')
        self.c = Controller(self.store)
        self.c.timer.stop()
        self.window = DashboardWindow(self.c, SyncWorker(self.store, Settings(enabled=False)))
        self.window.plot_timer.stop()
        self.view = self.window.diagnostic_view

    def tearDown(self):
        self.window.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_old_response_discarded_and_duplicate_suppressed(self):
        future = Future()
        self.view.rows = [{'origin': 'synthetic'}]
        self.view.episodes = [{'id': 'ev-1'}]
        self.view.url.setText('https://example.invalid/v1')
        self.view.model.setText('demo')
        self.view.key.setText('secret')
        with patch('motorlab.diagnostic_view.run_agents_async', return_value=future) as request, patch('motorlab.diagnostic_view.QTimer.singleShot'):
            self.view.analyze()
            self.view.analyze()
            self.assertEqual(request.call_count, 1)
            self.view.controls['current_max'].setValue(8)
            future.set_result({'propuesta': 'obsoleta'})
            self.view.poll()
        self.assertIsNone(self.view.result)
        self.assertIn('descartada', self.view.ai_text.toPlainText())

    def test_export_has_no_key(self):
        self.view.rows = [{'origin': 'synthetic'}]
        self.view.source = 'evaluation.csv'
        self.view.key.setText('super-secret-key')
        self.view.episodes = [{'id': 'ev-1'}]
        filename = str(Path(self.temp.name)/'report.json')
        with patch('motorlab.diagnostic_view.QFileDialog.getSaveFileName', return_value=(filename, '')):
            self.view.export_report()
        text = Path(filename).read_text()
        self.assertNotIn('super-secret-key', text)
        self.assertEqual(json.loads(text)['evidencias'][0]['id'], 'ev-1')

    def test_synthetic_csv_through_detection_agents_and_report(self):
        from motorlab.calibration import calibrate
        from motorlab.experiments import read_experiment
        from motorlab.synthetic import write_corpus
        files = write_corpus(Path(self.temp.name) / 'corpus')
        training = read_experiment(files['ajuste']['data'])
        validation = read_experiment(files['validacion']['data'])
        self.window.experiment, self.window.validation_experiment = training, validation
        self.window.calibration = calibrate(training, validation, steady_state=True)
        self.view.rows = read_experiment(files['combined']['data'])
        self.view.source = Path(files['combined']['data']).name
        self.view.steady.setChecked(True)
        self.view.slider.setRange(0, len(self.view.rows) - 1)
        self.view.detect()
        self.assertEqual({item['signal'] for item in self.view.episodes}, {'current', 'temperature'})
        self.assertTrue(self.view.residual_enabled)
        with patch('motorlab.diagnostic_view.QFileDialog.getOpenFileName', return_value=(files['combined']['labels'], '')):
            self.view.evaluate_labels()
        self.assertEqual(self.view.metrics['missed_count'], 0)
        self.assertEqual(self.view.metrics['false_alert_count'], 0)
        label_ids = [item['id'] for item in json.loads(Path(files['combined']['labels']).read_text())]
        evidence_id = self.view.episodes[0]['id']
        result = {'propuesta': {'hipotesis': [{'explicacion': 'Hipótesis', 'alternativas': 'Alternativa',
            'comprobaciones': 'Medir', 'evidencias': [evidence_id], 'componentes': ['bobinado']}]},
            'revision': {'hallazgos': [{'conclusion': 'Revisar', 'estado': 'insuficiente',
                'evidencias': [evidence_id], 'componentes': ['bobinado']}]}, 'error_revision': None}
        self.view.url.setText('https://example.invalid/v1')
        self.view.model.setText('test')
        self.view.key.setText('super-secret-key')
        requests = []
        def fake_async(config, evidence, context):
            from motorlab.ai import run_agents
            def opener(request, timeout):
                requests.append(json.loads(request.data))
                content = result['propuesta'] if len(requests) == 1 else result['revision']
                return io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(content)}}]}).encode())
            future = Future()
            future.set_result(run_agents(config, evidence, context, opener))
            return future
        with patch('motorlab.diagnostic_view.run_agents_async', side_effect=fake_async) as request, patch('motorlab.diagnostic_view.QTimer.singleShot'):
            self.view.analyze()
            payload = json.dumps(request.call_args.args[1:], ensure_ascii=False)
            for identifier in label_ids:
                self.assertNotIn(identifier, payload)
            self.assertNotIn('combinada.csv', payload)
            self.view.poll()
        self.assertEqual(len(requests), 2)
        self.assertEqual(self.view.result, result)
        self.assertIn('bobinado', self.view.detail.toPlainText())
        output = str(Path(self.temp.name) / 'informe.json')
        with patch('motorlab.diagnostic_view.QFileDialog.getSaveFileName', return_value=(output, '')):
            self.view.export_report()
        report = Path(output).read_text()
        self.assertNotIn('super-secret-key', report)
        self.assertEqual(json.loads(report)['metricas_evaluacion']['missed_count'], 0)
