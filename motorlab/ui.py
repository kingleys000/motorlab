"""Dos ventanas nativas Qt que comparten un único estado de simulación."""
from datetime import datetime
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from .model import SCENARIOS
from .storage import ROOT, Settings
from .theme import get_theme, themed
from .visualizer import MotorView, BG, CYAN, AMBER, TEXT, MUTED

STYLE = '''
QWidget { background: #0c1420; color: #e4edf7; font-family: "DejaVu Sans"; font-size: 12px; }
QMainWindow, QDialog { background: #0c1420; }
QLabel { background: transparent; }
QLabel#eyebrow { color: #4ee2cd; font-size: 10px; font-weight: bold; letter-spacing: 2px; }
QLabel#title { font-size: 25px; font-weight: bold; }
QLabel#muted { color: #8a9bb0; font-size: 11px; }
QLabel#value { font-size: 27px; font-weight: bold; }
QFrame#card { background: #121e2b; border: 1px solid #243444; border-radius: 10px; }
QFrame#card QLabel { background: transparent; border: none; }
QPushButton { background: #182939; border: 1px solid #304657; padding: 10px 13px; border-radius: 6px; min-height: 16px; }
QPushButton:hover { background: #243e4b; border-color: #4ee2cd; }
QPushButton:pressed { background: #304c55; }
QPushButton#primary { color: #071d1b; background: #4ee2cd; border: 1px solid #4ee2cd; font-weight: bold; }
QPushButton#primary:hover { background: #8cf7e6; }
QComboBox, QLineEdit, QDoubleSpinBox { background: #09121c; border: 1px solid #304657; border-radius: 5px; padding: 8px; min-height: 16px; selection-background-color: #235d58; }
QComboBox QAbstractItemView { background: #132131; selection-background-color: #235d58; }
QTextEdit { background: #09121c; border: 1px solid #243444; border-radius: 5px; padding: 6px; }
QTabWidget::pane { border: 1px solid #243444; }
QTabBar::tab { background: #142130; padding: 10px 18px; }
QTabBar::tab:selected { color: #4ee2cd; border-bottom: 2px solid #4ee2cd; }
QStatusBar { background: #09111a; color: #8a9bb0; }
QMenuBar, QMenu { background: #101d29; }
QMenuBar::item:selected, QMenu::item:selected { background: #245047; }
QScrollArea { border: none; }
QScrollBar:vertical { width: 9px; background: #101d29; }
QScrollBar::handle:vertical { background: #344b5d; border-radius: 4px; min-height: 20px; }
'''


def label(text, name=None):
    item = QLabel(text)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, primary=False):
    item = QPushButton(text)
    if primary:
        item.setObjectName('primary')
    item.clicked.connect(callback)
    return item


def card():
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(15, 13, 15, 13)
    layout.setSpacing(7)
    return frame, layout


class Metric(QFrame):
    def __init__(self, title, unit, color=CYAN):
        super().__init__()
        self.setObjectName('card')
        self.unit = unit
        self.base_color = color
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(label(title, 'muted'))
        self.value = label('—', 'value')
        self.value.setStyleSheet(f'color: {themed(color)}')
        layout.addWidget(self.value)
        layout.addWidget(label(unit, 'muted'))

    def set_value(self, value, decimals=1):
        self.value.setText(f'{value:,.{decimals}f}')

    def set_color(self, color):
        self.base_color = color
        self.refresh_color()

    def refresh_color(self):
        self.value.setStyleSheet(f'color: {themed(self.base_color)}')


class ConfigDialog(QDialog):
    def __init__(self, settings, parent):
        super().__init__(parent)
        self.setWindowTitle('Conexión · InfluxDB 3 Core')
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        layout.addWidget(label('CONECTAR TELEMETRÍA', 'eyebrow'))
        intro = label('Los datos quedan guardados localmente. Al conectar se enviarán\nlas muestras pendientes a la base configurada.', 'muted')
        layout.addWidget(intro)
        form = QFormLayout()
        self.host = QLineEdit(settings.host)
        self.database = QLineEdit(settings.database)
        self.token = QLineEdit(settings.token)
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText('Token de tu servidor InfluxDB 3')
        self.enabled = QCheckBox('Activar sincronización')
        self.enabled.setChecked(settings.enabled)
        self.persist = QCheckBox('Guardar configuración en .env privado de este proyecto')
        self.persist.setChecked(False)
        form.addRow('Servidor', self.host)
        form.addRow('Base de datos', self.database)
        form.addRow('Token', self.token)
        layout.addLayout(form)
        layout.addWidget(self.enabled)
        layout.addWidget(self.persist)
        layout.addWidget(label('Sin guardar, el token se utiliza sólo durante esta ejecución.', 'muted'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Aplicar conexión')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept_config)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_config(self):
        try:
            self.settings = Settings(self.host.text().strip(), self.database.text().strip(),
                                     self.token.text().strip(), self.enabled.isChecked())
            self.settings.validate()
            if self.persist.isChecked():
                self.settings.save()
            self.accept()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Configuración', str(exc))


class BaseWindow(QMainWindow):
    def __init__(self, controller, sync):
        super().__init__()
        self.c, self.sync = controller, sync
        self.theme = get_theme(STYLE)
        self.other = None
        menu = self.menuBar().addMenu('Laboratorio')
        for title, callback in (
            ('Iniciar / pausar', self.c.toggle), ('Nueva sesión', self.c.reset),
            ('Conectar InfluxDB…', self.configure), ('Modelo y guía de uso', self.guide),
            ('Salir de MotorLab', QApplication.instance().quit),
        ):
            action = menu.addAction(title)
            action.triggered.connect(callback)
        appearance = self.menuBar().addMenu('Apariencia')
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions = {}
        for mode, title in (('light', 'Modo claro'), ('dark', 'Modo oscuro')):
            action = appearance.addAction(title)
            action.setCheckable(True)
            action.setChecked(self.theme.mode == mode)
            self.theme_group.addAction(action)
            action.triggered.connect(lambda checked=False, chosen=mode: self.select_theme(chosen))
            self.theme_actions[mode] = action
        self.theme.changed.connect(self.apply_theme)
        toggle = QAction(self)
        toggle.setShortcut(QKeySequence('Ctrl+Space'))
        toggle.triggered.connect(self.c.toggle)
        self.addAction(toggle)
        sync.status.connect(self.update_status)
        self.statusBar().showMessage('Registro local activo · esperando conexión')

    def select_theme(self, mode):
        try:
            self.theme.set_mode(mode)
        except OSError as exc:
            QMessageBox.warning(self, 'Apariencia', 'El modo se aplicó, pero no se pudo guardar para el próximo inicio:\n' + str(exc))

    def apply_theme(self):
        for mode, action in self.theme_actions.items():
            action.setChecked(self.theme.mode == mode)
        for metric in self.findChildren(Metric):
            metric.refresh_color()

    def update_status(self, message, pending):
        self.statusBar().showMessage(f'{message}   •   {pending:,} muestras pendientes')

    def configure(self):
        dialog = ConfigDialog(self.sync.settings, self)
        if dialog.exec():
            self.sync.configure(dialog.settings)
            self.c.event.emit('Configuración de InfluxDB actualizada')

    def show_other(self):
        if self.other:
            self.other.show()
            self.other.raise_()
            self.other.activateWindow()

    def guide(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('MotorLab · guía del laboratorio')
        dialog.resize(690, 530)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText((ROOT / 'docs' / 'MODELO_Y_GUIA.md').read_text())
        layout.addWidget(text)
        layout.addWidget(button('Cerrar', dialog.accept))
        dialog.exec()

    def closeEvent(self, event):
        # Cerrar una ventana permite continuar con la otra; el botón la recupera.
        event.accept()
        if not self.other or not self.other.isVisible():
            QApplication.instance().quit()


class MotorWindow(BaseWindow):
    def __init__(self, controller, sync):
        super().__init__(controller, sync)
        self.setWindowTitle('MotorLab · visualizador del motor')
        self.resize(1040, 800)
        self.setMinimumSize(800, 630)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 12)
        layout.setSpacing(14)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label('MOTORLAB / LABORATORIO 01', 'eyebrow'))
        titles.addWidget(label('El movimiento, explicado.', 'title'))
        titles.addWidget(label('Motor DC · dinámica eléctrica, mecánica y térmica', 'muted'))
        top.addLayout(titles)
        top.addStretch()
        top.addWidget(button('Abrir dashboard  ↗', self.show_other))
        layout.addLayout(top)
        metrics = QHBoxLayout()
        self.rpm = Metric('VELOCIDAD', 'revoluciones / minuto')
        self.current = Metric('CORRIENTE', 'amperios', '#9aafff')
        self.temperature = Metric('TEMPERATURA', 'grados Celsius', AMBER)
        for item in (self.rpm, self.current, self.temperature):
            metrics.addWidget(item)
        layout.addLayout(metrics)
        body = QHBoxLayout()
        self.motor_view = MotorView(controller)
        body.addWidget(self.motor_view, 1)
        panel, controls = card()
        panel.setMinimumHeight(555)
        controls.addWidget(label('BANCO DE EXPERIMENTOS', 'eyebrow'))
        self.state = label('● EN PAUSA', 'muted')
        controls.addWidget(self.state)
        self.play = button('▶ Iniciar simulación', self.c.toggle, True)
        controls.addWidget(self.play)
        controls.addWidget(button('Experimento guiado · 90 s', self.c.start_demo))
        controls.addWidget(label('Escenario', 'muted'))
        self.scenarios = QComboBox()
        self.scenarios.addItems([*SCENARIOS, 'Personalizado'])
        self.scenarios.activated.connect(self.select_scenario)
        controls.addWidget(self.scenarios)
        self.inputs = {}
        for key, title, lo, hi, step, decimals, suffix in (
            ('voltage', 'Voltaje de alimentación', 0, 24, .5, 1, ' V'),
            ('load', 'Carga resistente', 0, 1.2, .01, 2, ' N·m'),
            ('cooling', 'Disipación térmica', .1, 2., .05, 2, ' W/K'),
        ):
            controls.addWidget(label(title, 'muted'))
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(step)
            spin.setDecimals(decimals)
            spin.setSuffix(suffix)
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(lambda value, field=key: self.c.set_input(field, value))
            self.inputs[key] = spin
            controls.addWidget(spin)
        controls.addWidget(label('Velocidad del tiempo', 'muted'))
        self.speed = QComboBox()
        self.speed.addItems(['Tiempo real · 1×', 'Acelerado · 2×', 'Acelerado · 5×'])
        self.speed.activated.connect(lambda index: setattr(self.c, 'speed', (1., 2., 5.)[index]))
        controls.addWidget(self.speed)
        controls.addStretch()
        controls.addWidget(button('Nueva sesión', self.c.reset))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(280)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        body.addWidget(scroll)
        layout.addLayout(body, 1)
        bottom = QHBoxLayout()
        self.clock = label('t = 0.00 s  ·  RK4 / Δt = 1 ms', 'muted')
        bottom.addWidget(self.clock)
        bottom.addStretch()
        bottom.addWidget(button('Modelo y ecuaciones', self.guide))
        layout.addLayout(bottom)
        self.c.changed.connect(self.refresh_controls)
        self.c.sample.connect(self.telemetry)
        self.c.reset_done.connect(lambda: self.telemetry(self.c.motor.snapshot()))
        self.c.timer.timeout.connect(self.refresh_clock)
        self.refresh_controls()
        self.telemetry(self.c.motor.snapshot())

    def apply_theme(self):
        super().apply_theme()
        self.refresh_controls()
        self.motor_view.update()

    def select_scenario(self, index):
        name = self.scenarios.itemText(index)
        if name in SCENARIOS:
            self.c.set_scenario(name)

    def refresh_controls(self):
        self.play.setText('Ⅱ Pausar simulación' if self.c.running else '▶ Iniciar simulación')
        self.state.setText('● SIMULANDO' if self.c.running else '● EN PAUSA')
        self.state.setStyleSheet(f'color: {themed(CYAN if self.c.running else MUTED)}')
        for key, spin in self.inputs.items():
            spin.blockSignals(True)
            spin.setValue(getattr(self.c.motor.inputs, key))
            spin.blockSignals(False)
        self.scenarios.setCurrentText(self.c.scenario)
        self.speed.setCurrentIndex((1., 2., 5.).index(self.c.speed))

    def telemetry(self, sample):
        self.rpm.set_value(sample['rpm'], 0)
        self.current.set_value(sample['current'], 2)
        self.temperature.set_value(sample['temperature'])
        self.temperature.set_color('#ff727f' if sample['temperature'] >= 80 else AMBER)

    def refresh_clock(self):
        self.clock.setText(f't = {self.c.motor.time:7.2f} s   ·   RK4 / Δt = 1 ms   ·   sesión {self.c.session[:6]}')


class DashboardWindow(BaseWindow):
    def __init__(self, controller, sync):
        super().__init__(controller, sync)
        self.setWindowTitle('MotorLab · dashboard de telemetría')
        self.resize(1070, 800)
        self.setMinimumSize(800, 650)
        self.history_session = None
        self.historical = []
        self.dirty = True
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 12)
        layout.setSpacing(12)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label('MOTORLAB / TELEMETRÍA', 'eyebrow'))
        titles.addWidget(label('Cada cambio deja una curva.', 'title'))
        titles.addWidget(label('10 muestras/s simulados · historial local · destino InfluxDB 3', 'muted'))
        top.addLayout(titles)
        top.addStretch()
        top.addWidget(button('Ver motor  ↗', self.show_other))
        layout.addLayout(top)
        toolbar = QHBoxLayout()
        self.sessions = QComboBox()
        self.sessions.setMinimumWidth(270)
        self.sessions.activated.connect(self.select_session)
        toolbar.addWidget(self.sessions, 1)
        toolbar.addWidget(button('Actualizar historial', self.refresh_sessions))
        toolbar.addWidget(button('Exportar CSV', self.export))
        toolbar.addWidget(button('Conectar InfluxDB', self.configure))
        layout.addLayout(toolbar)
        metrics = QHBoxLayout()
        self.power_in = Metric('POTENCIA ELÉCTRICA', 'W', '#9aafff')
        self.power_out = Metric('POTENCIA EN LA CARGA', 'W', CYAN)
        self.torque = Metric('PAR ELECTROMAGNÉTICO', 'N·m', AMBER)
        self.samples_metric = Metric('MUESTRAS EN LA VISTA', 'últimos 600 s en modo vivo', '#e4edf7')
        for item in (self.power_in, self.power_out, self.torque, self.samples_metric):
            metrics.addWidget(item)
        layout.addLayout(metrics)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        plots_container = QWidget()
        plots_layout = QGridLayout(plots_container)
        plots_layout.setContentsMargins(6, 8, 6, 6)
        self.plots = {}
        self.curves = {}
        self.plot_metadata = {}
        pg.setConfigOptions(antialias=True, foreground=MUTED, background=BG)
        for index, (key, title, unit, color) in enumerate((
            ('rpm', 'Velocidad del rotor', 'RPM', CYAN),
            ('current', 'Corriente de armadura', 'A', '#9aafff'),
            ('temperature', 'Temperatura del bobinado', '°C', AMBER),
            ('voltage', 'Voltaje aplicado', 'V', '#74b8ff'),
        )):
            plot = pg.PlotWidget()
            plot.setTitle(title, color=TEXT, size='11pt')
            plot.setLabel('left', unit)
            plot.setLabel('bottom', 'Tiempo simulado', units='s')
            plot.showGrid(x=True, y=True, alpha=.16)
            plot.setMenuEnabled(False)
            plot.setMinimumSize(250, 155)
            plot.getPlotItem().hideButtons()
            curve = plot.plot(pen=pg.mkPen(color, width=2))
            curve.setClipToView(True)
            curve.setDownsampling(auto=True, method='peak')
            if key == 'temperature':
                plot.addItem(pg.InfiniteLine(pos=80, angle=0, pen=pg.mkPen('#b46152', style=Qt.PenStyle.DashLine)))
                plot.setYRange(20, 90, padding=0)
            elif key == 'voltage':
                plot.setYRange(-1, 25, padding=0)
            self.plots[key], self.curves[key] = plot, curve
            self.plot_metadata[key] = (title, unit, color)
            plots_layout.addWidget(plot, index//2, index%2)
        self.tabs.addTab(plots_container, 'Señales')
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(500)
        self.tabs.addTab(self.log, 'Bitácora')
        dbpage = QWidget()
        dblayout = QVBoxLayout(dbpage)
        dblayout.addWidget(label('Consulta real al servidor: las diez muestras más recientes de motor_dc.', 'muted'))
        self.query_button = button('Consultar InfluxDB', self.query)
        dblayout.addWidget(self.query_button)
        self.query_text = QTextEdit()
        self.query_text.setReadOnly(True)
        self.query_text.setPlainText('Configura la conexión y ejecuta una simulación para consultar sus datos.\n\nEl historial del selector superior procede del registro local.')
        dblayout.addWidget(self.query_text)
        self.tabs.addTab(dbpage, 'Datos en InfluxDB')
        self.bottom = label('EN VIVO · rueda para zoom · arrastra para desplazar · doble clic para reencuadrar', 'muted')
        layout.addWidget(self.bottom)
        self.c.sample.connect(self.on_sample)
        self.c.event.connect(self.log_event)
        self.c.reset_done.connect(self.new_session)
        sync.query_result.connect(self.query_result)
        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(100)
        self.plot_timer.timeout.connect(self.redraw)
        self.plot_timer.start()
        self.refresh_sessions()
        self.log_event('Laboratorio listo. Inicia el motor o ejecuta el experimento guiado.')
        self.update_metrics(self.c.motor.snapshot(), 0)
        self.apply_theme()

    def apply_theme(self):
        super().apply_theme()
        for key, plot in self.plots.items():
            title, unit, color = self.plot_metadata[key]
            plot.setBackground(themed(BG))
            plot.setTitle(title, color=themed(TEXT), size='11pt')
            plot.setLabel('left', unit, color=themed(MUTED))
            plot.setLabel('bottom', 'Tiempo simulado', units='s', color=themed(MUTED))
            for side in ('left', 'bottom', 'right', 'top'):
                axis = plot.getAxis(side)
                axis.setPen(pg.mkPen(themed(MUTED)))
                axis.setTextPen(pg.mkPen(themed(MUTED)))
            self.curves[key].setPen(pg.mkPen(themed(color), width=2))

    def log_event(self, text):
        self.log.append(f'[{datetime.now():%H:%M:%S}]  t={self.c.motor.time:.2f} s  ·  {text}')

    def refresh_sessions(self):
        selected = self.history_session
        self.sessions.clear()
        self.sessions.addItem('● En vivo · sesión actual', None)
        for sid, created, count in self.c.store.sessions():
            if sid == self.c.session or count == 0:
                continue
            local = datetime.fromisoformat(created).astimezone().strftime('%d/%m %H:%M:%S')
            self.sessions.addItem(f'{local} · {sid[:6]} · {count:,} muestras', sid)
        index = self.sessions.findData(selected)
        self.sessions.setCurrentIndex(max(0, index))

    def select_session(self, index):
        self.history_session = self.sessions.itemData(index)
        self.historical = self.c.store.samples(self.history_session) if self.history_session else []
        self.dirty = True
        self.bottom.setText('HISTORIAL LOCAL · la simulación puede seguir ejecutándose en la otra ventana' if self.history_session
                            else 'EN VIVO · ventana móvil de 60 s · datos completos en el historial y CSV')
        for plot in self.plots.values():
            plot.enableAutoRange()
        self.redraw()

    def new_session(self):
        self.history_session = None
        self.historical = []
        self.refresh_sessions()
        self.dirty = True
        self.bottom.setText('EN VIVO · nueva sesión')
        self.update_metrics(self.c.motor.snapshot(), 0)

    def on_sample(self, sample):
        if not self.history_session:
            self.dirty = True

    def update_metrics(self, point, count):
        self.power_in.set_value(point['power_in'])
        self.power_out.set_value(point['power_out'])
        self.torque.set_value(point['torque'], 3)
        self.samples_metric.set_value(count, 0)

    def redraw(self):
        if not self.dirty:
            return
        self.dirty = False
        data = self.historical if self.history_session else list(self.c.history)
        times = [point['sim_time'] for point in data]
        for key, curve in self.curves.items():
            curve.setData(times, [point[key] for point in data])
            if not self.history_session and times:
                end = max(10, times[-1])
                self.plots[key].setXRange(max(0, end-60), end, padding=.01)
        if data:
            self.update_metrics(data[-1], len(data))
        else:
            self.update_metrics(self.c.motor.snapshot(), 0)
            for plot in self.plots.values():
                plot.setXRange(0, 10, padding=.01)

    def export(self):
        session = self.history_session or self.c.session
        directory = ROOT / 'exports'
        directory.mkdir(exist_ok=True)
        name, _ = QFileDialog.getSaveFileName(self, 'Exportar sesión completa', str(directory / f'motor_{session}.csv'), 'CSV (*.csv)')
        if name:
            try:
                self.c.store.export(session, name)
                self.log_event('Exportación CSV completada')
                QMessageBox.information(self, 'Exportación', f'Sesión exportada a:\n{name}')
            except OSError as exc:
                QMessageBox.warning(self, 'No se pudo exportar', str(exc))

    def query(self):
        self.query_button.setEnabled(False)
        self.query_text.setPlainText('Consultando el servidor…')
        self.sync.check()

    def query_result(self, message):
        self.query_button.setEnabled(True)
        self.query_text.setPlainText(message)
