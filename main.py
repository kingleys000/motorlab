"""Punto de entrada: .venv/bin/python main.py"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description='MotorLab · laboratorio de simulación continua')
    parser.add_argument('--smoke', action='store_true', help='Ejecutar comprobación gráfica sin ventanas visibles')
    parser.add_argument('--capture-dir', help='Directorio para capturas de la comprobación gráfica')
    args = parser.parse_args()
    if args.smoke:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    from pathlib import Path
    import tempfile
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from motorlab.controller import Controller
    from motorlab.storage import SessionStore, Settings, SyncWorker
    from motorlab.ui import MotorWindow, DashboardWindow, STYLE
    from motorlab.theme import ThemeManager

    app = QApplication(sys.argv[:1])
    app.setApplicationName('MotorLab')
    app.setOrganizationName('Laboratorio de Modelado y Simulación')
    app.setStyle('Fusion')
    temporary = tempfile.TemporaryDirectory(prefix='motorlab-smoke-') if args.smoke else None
    app.motorlab_theme = ThemeManager(STYLE, Path(temporary.name) / 'preferences.json' if temporary else None)
    store = SessionStore(Path(temporary.name) / 'telemetry.sqlite3' if temporary else None)
    settings = Settings(enabled=False) if args.smoke else Settings.load()
    controller = Controller(store)
    sync = SyncWorker(store, settings)
    motor = MotorWindow(controller, sync)
    dashboard = DashboardWindow(controller, sync)
    motor.other, dashboard.other = dashboard, motor
    controller.failure.connect(lambda message: QMessageBox.warning(motor, 'Registro de datos', message))
    screen = app.primaryScreen().availableGeometry()
    if screen.width() >= 1800:
        w = min(1040, (screen.width()-50)//2)
        h = min(800, screen.height()-70)
        motor.resize(w, h)
        dashboard.resize(w, h)
        motor.move(screen.x()+10, screen.y()+25)
        dashboard.move(screen.x()+w+30, screen.y()+25)
    else:
        w, h = min(1000, screen.width()-60), min(780, screen.height()-75)
        motor.resize(w, h)
        dashboard.resize(w, h)
        motor.move(screen.x()+20, screen.y()+20)
        dashboard.move(screen.x()+45, screen.y()+45)
    dashboard.show()
    motor.show()
    motor.raise_()
    sync.start()
    app.aboutToQuit.connect(controller.timer.stop)
    app.aboutToQuit.connect(sync.stop)
    if args.smoke:
        controller.start_demo()
        def finish():
            try:
                assert len(controller.history) > 10, 'La simulación no produjo suficientes muestras.'
                assert store.samples(controller.session), 'No se guardaron muestras.'
                if args.capture_dir:
                    target = Path(args.capture_dir)
                    target.mkdir(parents=True, exist_ok=True)
                    motor.grab().save(str(target / 'motorlab-motor.png'))
                    dashboard.grab().save(str(target / 'motorlab-dashboard.png'))
                print(f'SMOKE OK: dos ventanas, {len(controller.history)} muestras y registro local.', flush=True)
                app.quit()
            except Exception as exc:
                print(f'SMOKE ERROR: {exc}', file=sys.stderr, flush=True)
                app.exit(1)
        QTimer.singleShot(4500, finish)
    code = app.exec()
    if temporary:
        temporary.cleanup()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
