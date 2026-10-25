"""Verifica interacciones y un experimento completo sin tocar la base real."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from pathlib import Path
import tempfile
import time
import unittest

from PySide6.QtWidgets import QApplication
from motorlab.controller import Controller
from motorlab.storage import SessionStore, Settings, SyncWorker
from motorlab.ui import MotorWindow, DashboardWindow, STYLE
from motorlab.theme import ThemeManager


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app.motorlab_theme = ThemeManager(STYLE, Path(self.temp.name) / 'preferences.json')
        self.store = SessionStore(Path(self.temp.name) / 'test.sqlite3')
        self.controller = Controller(self.store)
        self.controller.timer.stop()

    def tearDown(self):
        self.temp.cleanup()

    def test_full_guided_experiment_and_saved_history(self):
        c = self.controller
        events = []
        c.event.connect(events.append)
        c.start_demo()
        session = c.session
        for _ in range(100):
            if not c.running:
                break
            c.previous = time.monotonic() - .201
            c.tick()
        self.assertFalse(c.running)
        self.assertAlmostEqual(c.motor.time, 90, delta=.002)
        samples = self.store.samples(session)
        self.assertEqual(len(samples), 900)
        self.assertEqual({sample['voltage'] for sample in samples}, {0.0, 18.0, 24.0})
        self.assertTrue(any(sample['current'] < 0 for sample in samples))
        self.assertTrue(any('Experimento completo' in event for event in events))
        c.reset()
        self.assertNotEqual(c.session, session)
        self.assertEqual(len(self.store.samples(session)), 900)
        self.assertEqual(len(c.history), 0)

    def test_two_windows_controls_and_history(self):
        c = self.controller
        sync = SyncWorker(self.store, Settings(enabled=False))
        motor = MotorWindow(c, sync)
        dashboard = DashboardWindow(c, sync)
        dashboard.plot_timer.stop()
        motor.other, dashboard.other = dashboard, motor
        try:
            motor.resize(800, 725)
            motor.show()
            dashboard.show()
            self.app.processEvents()

            self.assertGreaterEqual(motor.play.height(), 30)
            self.assertGreaterEqual(motor.inputs['voltage'].height(), 30)
            motor.inputs['voltage'].setValue(12)
            self.assertEqual(c.motor.inputs.voltage, 12)
            motor.play.click()
            self.assertTrue(c.running)
            for _ in range(4):
                c.previous = time.monotonic() - .201
                c.tick()
            previous = c.session
            c.reset()
            index = dashboard.sessions.findData(previous)
            self.assertGreater(index, 0)
            dashboard.sessions.setCurrentIndex(index)
            dashboard.select_session(index)
            self.assertEqual(dashboard.history_session, previous)
            self.assertGreater(len(dashboard.historical), 0)
            self.assertEqual(dashboard.historical[-1]['voltage'], 12)
            dashboard.select_session(0)
            self.assertIsNone(dashboard.history_session)
            motor.close()
            self.assertTrue(dashboard.isVisible())
            dashboard.show_other()
            self.assertTrue(motor.isVisible())
        finally:
            motor.hide()
            dashboard.hide()
            motor.deleteLater()
            dashboard.deleteLater()
            self.app.processEvents()


    def test_theme_changes_both_windows_and_survives_restart(self):
        c = self.controller
        sync = SyncWorker(self.store, Settings(enabled=False))
        motor = MotorWindow(c, sync)
        dashboard = DashboardWindow(c, sync)
        dashboard.plot_timer.stop()
        theme = self.app.motorlab_theme
        try:
            motor.show()
            dashboard.show()
            self.app.processEvents()
            original = (c.session, c.motor.time, c.running)
            dashboard.plots['rpm'].setXRange(5, 20, padding=0)
            motor.theme_actions['light'].trigger()
            self.app.processEvents()
            self.assertTrue(dashboard.theme_actions['light'].isChecked())
            self.assertFalse(dashboard.theme_actions['dark'].isChecked())
            self.assertEqual(dashboard.curves['rpm'].opts['pen'].color().name(), '#007f70')
            self.assertEqual(motor.motor_view.grab().toImage().pixelColor(2, 2).name(), '#f8fafc')
            self.assertEqual(dashboard.plots['rpm'].getViewBox().viewRange()[0], [5, 20])
            self.assertEqual((c.session, c.motor.time, c.running), original)
            restored = ThemeManager(STYLE, theme.path)
            self.assertEqual(restored.mode, 'light')
            restored.deleteLater()
            dashboard.theme_actions['dark'].trigger()
            self.app.processEvents()
            self.assertTrue(motor.theme_actions['dark'].isChecked())
            self.assertEqual(dashboard.curves['rpm'].opts['pen'].color().name(), '#4ee2cd')
            self.assertEqual(motor.motor_view.grab().toImage().pixelColor(2, 2).name(), '#0a111b')
        finally:
            motor.hide()
            dashboard.hide()
            motor.deleteLater()
            dashboard.deleteLater()
            self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
