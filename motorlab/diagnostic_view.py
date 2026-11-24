"""Ensayo evaluado, evidencias y visor local; independiente de la calibración."""
from dataclasses import asdict
from html import escape
import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QScrollArea, QSlider, QSplitter, QTextEdit, QVBoxLayout, QWidget)

from .ai import AIConfig, run_agents_async
from .experiments import read_experiment


class ViewerBridge(QObject):
    command = Signal(str)
    loaded = Signal()

    @Slot()
    def ready(self):
        self.loaded.emit()

    def send(self, action, **values):
        self.command.emit(json.dumps({'action': action, **values}, ensure_ascii=False))


class DiagnosticView(QWidget):
    def __init__(self, dashboard):
        super().__init__(dashboard)
        self.dashboard = dashboard
        self.rows = []
        self.source = ''
        self.episodes = []
        self.detected = False
        self.residual_enabled = False
        self.metrics = None
        self.result = None
        self.future = None
        self.revision = 0
        self.viewer = None
        self.bridge = ViewerBridge(self)
        self.bridge.loaded.connect(self.sync_viewer)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(self.make_button('Importar CSV de evaluación', self.load_csv))
        top.addWidget(self.make_button('Detectar episodios', self.detect))
        top.addWidget(self.make_button('Evaluar etiquetas', self.evaluate_labels))
        top.addWidget(self.make_button('Exportar informe JSON', self.export_report))
        root.addLayout(top)
        notice = QLabel('Referencias didácticas editables; no son límites de un motor físico. El ensayo evaluado nunca recalibra el modelo.')
        notice.setWordWrap(True)
        form = QFormLayout()
        self.controls = {}
        for name, title, value in [('current_max', 'Corriente máxima (A)', 3.0),
                ('temperature_max', 'Temperatura máxima (°C)', 40.0),
                ('voltage_residual_max', 'Residual máximo (V)', 0.5),
                ('persistence_s', 'Persistencia (s)', 1.0), ('clear_s', 'Limpieza (s)', 0.5)]:
            box = QDoubleSpinBox()
            box.setRange(0 if name.endswith('_s') else .0001, 100000)
            box.setDecimals(3)
            box.setValue(value)
            box.valueChanged.connect(self.invalidate)
            self.controls[name] = box
            form.addRow(title, box)
        self.steady = QCheckBox('Declaro que el ensayo evaluado está en régimen estacionario')
        self.steady.toggled.connect(self.invalidate)
        form.addRow(self.steady)
        split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(split, 1)
        self.viewer_container = QWidget()
        self.viewer_layout = QVBoxLayout(self.viewer_container)
        self.viewer_status = QLabel('El visor 3D se carga al abrir esta pestaña. Si WebGL falla, las evidencias permanecen disponibles.')
        self.viewer_status.setWordWrap(True)
        self.viewer_layout.addWidget(self.viewer_status)
        split.addWidget(self.viewer_container)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.observation_label = QLabel('● Anomalías observadas · seleccione un episodio')
        right_layout.addWidget(self.observation_label)
        self.list = QListWidget()
        self.list.setMinimumHeight(110)
        self.list.setMaximumHeight(140)
        self.list.currentRowChanged.connect(self.select_episode)
        right_layout.addWidget(self.list, 1)
        self.component = QComboBox()
        for text, identifier in [('Motor completo', 'motor'), ('Bobinado', 'bobinado'),
                                 ('Rotor / eje', 'rotor_eje'), ('Carcasa', 'carcasa'),
                                 ('Estator', 'estator'), ('Escobillas', 'escobillas'),
                                 ('Conmutador', 'conmutador'), ('Rodamientos', 'rodamientos')]:
            self.component.addItem(text, identifier)
        self.component.currentIndexChanged.connect(self.select_component)
        right_layout.addWidget(QLabel('◆ Selección visual manual (no implica avería)'))
        right_layout.addWidget(self.component)
        right_layout.addWidget(self.make_button('Abrir vista explotada', lambda: self.bridge.send('explode')))
        right_layout.addWidget(self.make_button('Restaurar vista', self.restore_view))
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(130)
        right_layout.addWidget(self.detail, 1)
        right_layout.addWidget(notice)
        right_layout.addLayout(form)
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setWidget(right)
        split.addWidget(scroller)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        play = QHBoxLayout()
        self.play_button = self.make_button('▶ Reproducir', self.toggle_play)
        play.addWidget(self.play_button)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self.show_sample)
        play.addWidget(self.slider, 1)
        self.sample_label = QLabel('Sin muestras')
        play.addWidget(self.sample_label)
        root.addLayout(play)
        ai_form = QFormLayout()
        self.provider = QLineEdit('Compatible con OpenAI')
        self.url = QLineEdit()
        self.url.setPlaceholderText('https://proveedor/v1')
        self.model = QLineEdit()
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        for field, widget in [('Proveedor', self.provider), ('URL base API', self.url), ('Modelo', self.model), ('Clave (solo sesión)', self.key)]:
            ai_form.addRow(field, widget)
        right_layout.addLayout(ai_form)
        right_layout.addWidget(self.make_button('Consultar diagnóstico y revisión IA', self.analyze))
        self.ai_text = QTextEdit()
        self.ai_text.setReadOnly(True)
        self.ai_text.setMaximumHeight(135)
        self.ai_text.setPlainText('Sin análisis IA. La revisión no confirma una avería física.')
        right_layout.addWidget(self.ai_text)

    @staticmethod
    def make_button(text, callback):
        item = QPushButton(text)
        item.clicked.connect(callback)
        return item

    def init_viewer(self):
        if self.viewer is not None:
            return
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtWebChannel import QWebChannel
            self.viewer = QWebEngineView(self)
            channel = QWebChannel(self.viewer.page())
            channel.registerObject('bridge', self.bridge)
            self.viewer.page().setWebChannel(channel)
            self.channel = channel
            self.viewer.loadFinished.connect(self.viewer_loaded)
            self.viewer.setUrl(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / 'web' / 'index.html')))
            self.viewer_layout.addWidget(self.viewer, 1)
        except (ImportError, RuntimeError):
            self.viewer_status.setText('Visor 3D no disponible; las alertas y el dashboard siguen disponibles.')

    def viewer_loaded(self, ok):
        self.viewer_status.setText('Visor 3D local · si WebGL no está disponible, consulta las evidencias a la derecha.' if ok
                                   else 'No se pudo cargar el visor 3D; las evidencias siguen disponibles.')

    def sync_viewer(self):
        self.set_theme(self.dashboard.theme.mode)
        self.show_sample(self.slider.value())
        self.select_episode(self.list.currentRow())

    def set_theme(self, mode):
        self.observation_label.setStyleSheet('color: ' + ('#bc2840' if mode == 'light' else '#ff727f') + '; font-weight: bold')
        if 0 <= self.list.currentRow() < len(self.episodes):
            self.render_episode_detail(self.episodes[self.list.currentRow()])
        self.bridge.send('theme', mode=mode)

    def invalidate(self, *_):
        self.revision += 1
        self.episodes = []
        self.detected = False
        self.residual_enabled = False
        self.metrics = None
        self.result = None
        self.list.clear()
        self.detail.clear()
        self.ai_text.setPlainText('El contexto cambió. Ejecute la detección nuevamente.')
        self.bridge.send('select', components=[])

    def load_csv(self):
        name, _ = QFileDialog.getOpenFileName(self, 'Ensayo de evaluación', '', 'CSV (*.csv)')
        if not name:
            return
        try:
            rows = read_experiment(name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Ensayo inválido', str(exc))
            return
        self.timer.stop()
        self.rows = rows
        self.source = Path(name).name
        self.invalidate()
        self.slider.setRange(0, len(rows)-1)
        self.slider.setValue(0)
        self.show_sample(0)

    def detect(self):
        from .diagnostics import detect_episodes, Limits
        if not self.rows:
            QMessageBox.information(self, 'Detección', 'Importa primero un CSV de evaluación.')
            return
        calibration = self.dashboard.calibration
        residual = bool(calibration and self.steady.isChecked() and
                        self.rows != self.dashboard.experiment and self.rows != self.dashboard.validation_experiment and
                        all(row['origin'] == calibration.origin and row['sensor_location'].lower() in ('bobinado', 'winding') for row in self.rows))
        values = {key: widget.value() for key, widget in self.controls.items()}
        if not residual:
            values['voltage_residual_max'] = None
        limits = Limits(**values)
        self.invalidate()
        from .calibration import compare
        try:
            predictions = compare(self.rows, calibration.parameters) if residual else None
            self.episodes = detect_episodes(
                self.rows, limits,
                predicted_voltages=[p['predicted_voltage'] for p in predictions] if predictions else None,
                steady_state=residual, calibration=calibration if residual else None)
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, 'No se pudo analizar el ensayo', str(exc))
            return
        # No presentar las hipótesis heredadas del detector como observaciones.
        self.episodes = [{k: v for k, v in episode.items() if k != 'hypothesis'} for episode in self.episodes]
        self.detected = True
        self.residual_enabled = residual
        for episode in self.episodes:
            self.list.addItem(f"● {episode['signal']} · {episode['start_time']:.2f}–{episode['end_time']:.2f} s · {episode['id']}")
        self.detail.setPlainText(f'{len(self.episodes)} episodios observados. ' + ('Residual habilitado.' if residual else 'Residual deshabilitado: requiere calibración compatible y supuesto estacionario declarado.'))
        if self.episodes:
            self.list.setCurrentRow(0)

    def evaluate_labels(self):
        if not self.detected:
            QMessageBox.information(self, 'Evaluación', 'Ejecuta primero la detección del ensayo.')
            return
        name, _ = QFileDialog.getOpenFileName(self, 'Etiquetas independientes para evaluación', '', 'JSON (*.json)')
        if not name:
            return
        self.metrics = None
        try:
            from .evaluation import evaluate_episodes
            labels = json.loads(Path(name).read_text(encoding='utf-8'))
            self.metrics = evaluate_episodes(self.episodes, labels)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, 'Etiquetas inválidas', str(exc))
            return
        self.detail.setPlainText('Métricas de evaluación sintética (etiquetas independientes):\n' +
                                 json.dumps(self.metrics, ensure_ascii=False, indent=2))

    def select_episode(self, index):
        if index < 0 or index >= len(self.episodes):
            self.bridge.send('select', components=[])
            return
        episode = self.episodes[index]
        related = []
        if self.result:
            for item in self.result['propuesta']['hipotesis']:
                if episode['id'] in item['evidencias']:
                    related.extend(item['componentes'])
        related = sorted(set(related))
        self.component.blockSignals(True)
        if self.component.itemData(0) == 'related':
            self.component.removeItem(0)
        self.episode_components = related
        if related:
            self.component.insertItem(0, 'Posibles relacionados según IA', 'related')
        self.component.setCurrentIndex(0)
        self.component.blockSignals(False)
        self.render_episode_detail(episode)
        self.select_component()
        if self.rows:
            start = episode['start_time']
            self.slider.setValue(min(range(len(self.rows)), key=lambda i: abs(self.rows[i]['acquisition_time']-start)))

    def render_episode_detail(self, episode):
        related = self.episode_components
        description = (', '.join(related) + ' (hipótesis IA, no fallas confirmadas)' if related
                       else 'motor completo (la medición no localiza una pieza)')
        dark = self.dashboard.theme.mode == 'dark'
        observed_color = '#ff727f' if dark else '#bc2840'
        possible_color = '#4ee2cd' if dark else '#007f70'
        selected_color = '#e6b535' if dark else '#795400'
        self.detail.setHtml(f'<p style="color:{observed_color}">● Anomalía observada</p><pre>' +
            escape(json.dumps(episode, ensure_ascii=False, indent=2)) +
            f'</pre><p style="color:{possible_color}">◇ Posibles componentes relacionados: ' +
            escape(description) + f'</p><p style="color:{selected_color}">◆ Selección visual: no implica avería.</p>')

    def select_component(self, *_):
        if self.list.currentRow() >= 0:
            selection = self.component.currentData()
            self.bridge.send('select', components=self.episode_components if selection == 'related' else [selection])

    def restore_view(self):
        self.list.setCurrentRow(-1)
        self.component.setCurrentIndex(0)
        self.bridge.send('reset')
        self.detail.setPlainText('Vista restaurada. Seleccione un episodio para ver su evidencia.')

    def show_sample(self, index):
        if not self.rows:
            return
        row = self.rows[index]
        self.sample_label.setText(f"t={row['acquisition_time']:.2f} s · {row['rpm']:.0f} RPM")
        self.bridge.send('sample', rpm=row['rpm'], playing=self.timer.isActive())

    def toggle_play(self):
        if not self.rows:
            return
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText('▶ Reproducir')
        else:
            if self.slider.value() == self.slider.maximum(): self.slider.setValue(0)
            index = self.slider.value()
            interval = (self.rows[index + 1]['acquisition_time'] - self.rows[index]['acquisition_time']
                        if index + 1 < len(self.rows) else 0.1)
            self.timer.start(max(1, int(interval * 1000)))
            self.play_button.setText('❚❚ Pausar')
        self.show_sample(self.slider.value())

    def advance(self):
        i = self.slider.value()
        if i >= self.slider.maximum():
            self.toggle_play()
            return
        self.slider.setValue(i+1)
        if i+1 == self.slider.maximum():
            self.toggle_play()
            return
        if i+2 < len(self.rows):
            dt = self.rows[i+2]['acquisition_time'] - self.rows[i+1]['acquisition_time']
            self.timer.setInterval(max(1, int(dt * 1000)))

    def context(self):
        return {'origen': self.rows[0]['origin'] if self.rows else None,
                'perfil': self.dashboard.profile.identifier,
                'version_perfil': self.dashboard.profile.version,
                'calibracion': asdict(self.dashboard.calibration) if self.dashboard.calibration else None,
                'regimen_estacionario_declarado': self.steady.isChecked(),
                'diagnostico_residual_habilitado': self.residual_enabled,
                'limites_didacticos': {k: w.value() for k, w in self.controls.items()}}

    def analyze(self):
        if not self.episodes:
            QMessageBox.information(self, 'IA', 'Detecta primero los episodios observados.')
            return
        if self.future is not None:
            return
        config = AIConfig(self.url.text().strip(), self.model.text().strip(), self.key.text(), provider=self.provider.text().strip())
        try:
            config.validate()
        except ValueError as exc:
            self.ai_text.setPlainText(str(exc))
            return
        self.result = None
        self.select_episode(self.list.currentRow())
        self.future_revision = self.revision
        self.future = run_agents_async(config, self.episodes, self.context())
        self.ai_text.setPlainText('Consultando agentes secuencialmente en segundo plano…')
        QTimer.singleShot(100, self.poll)

    def poll(self):
        if not self.future.done():
            QTimer.singleShot(100, self.poll)
            return
        future, self.future = self.future, None
        if self.future_revision != self.revision:
            self.ai_text.setPlainText('Respuesta anterior descartada porque cambió el contexto.')
            return
        try:
            self.result = future.result()
            self.ai_text.setPlainText('Interpretaciones, no confirmación física:\n' + json.dumps(self.result, ensure_ascii=False, indent=2))
            self.select_episode(self.list.currentRow())
        except RuntimeError as exc:
            message = str(exc)
            if self.key.text():
                message = message.replace(self.key.text(), '[credencial]')
            self.ai_text.setPlainText(message + ' Puede reintentar manualmente.')
        except Exception:
            self.ai_text.setPlainText('No se pudo obtener una propuesta válida. Puede reintentar manualmente.')

    def export_report(self):
        if not self.rows:
            return
        name, _ = QFileDialog.getSaveFileName(self, 'Informe del análisis', 'motorlab_informe.json', 'JSON (*.json)')
        if not name:
            return
        report = {'version_informe': 1, 'archivo_datos': self.source, 'contexto': self.context(), 'evidencias': self.episodes,
                  'interpretaciones': self.result, 'metricas_evaluacion': self.metrics, 'validacion_fisica': False}
        try:
            Path(name).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Exportación', str(exc))
