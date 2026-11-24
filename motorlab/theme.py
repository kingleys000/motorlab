"""Tema compartido por todas las ventanas y preferencia local de apariencia."""
import json
from pathlib import Path
import re

from PySide6.QtCore import QObject, QIODevice, QSaveFile, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


# La paleta original es oscura. Los acentos claros usan tonos más profundos
# para conservar el contraste sobre superficies blancas.
LIGHT_COLORS = {
    '#0c1420': '#eef3f8', '#e4edf7': '#172c3f', '#4ee2cd': '#007f70',
    '#8a9bb0': '#506579', '#121e2b': '#ffffff', '#243444': '#cbd7e2',
    '#182939': '#e6edf4', '#304657': '#b4c5d4', '#243e4b': '#d5e8e4',
    '#304c55': '#c1dfd7', '#071d1b': '#ffffff', '#8cf7e6': '#00685c',
    '#09121c': '#ffffff', '#235d58': '#bdded5', '#132131': '#ffffff',
    '#142130': '#e4edf5', '#09111a': '#e4edf5', '#101d29': '#e4edf5',
    '#245047': '#cde5df', '#344b5d': '#9daebe', '#0a111b': '#f8fafc',
    '#142231': '#dce5ed', '#ffba6b': '#a65400', '#9aafff': '#5453b8',
    '#74b8ff': '#2167a6', '#ff727f': '#bc2840',
}


class ThemeManager(QObject):
    changed = Signal()

    def __init__(self, stylesheet, path=None):
        super().__init__(QApplication.instance())
        self.dark_stylesheet = stylesheet
        self.path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / 'data' / 'preferences.json'
        self.mode = 'dark'
        try:
            preferences = json.loads(self.path.read_text())
            if isinstance(preferences, dict) and preferences.get('theme') in ('light', 'dark'):
                self.mode = preferences['theme']
        except (OSError, ValueError):
            pass
        self.apply()

    def resolve(self, color):
        return LIGHT_COLORS.get(color.lower(), color) if self.mode == 'light' else color

    def apply(self):
        app = QApplication.instance()
        palette = QPalette(app.style().standardPalette())
        for role, value in (
            (QPalette.ColorRole.Window, '#0c1420'),
            (QPalette.ColorRole.WindowText, '#e4edf7'),
            (QPalette.ColorRole.Base, '#09121c'),
            (QPalette.ColorRole.AlternateBase, '#121e2b'),
            (QPalette.ColorRole.Text, '#e4edf7'),
            (QPalette.ColorRole.Button, '#182939'),
            (QPalette.ColorRole.ButtonText, '#e4edf7'),
            (QPalette.ColorRole.ToolTipBase, '#121e2b'),
            (QPalette.ColorRole.ToolTipText, '#e4edf7'),
            (QPalette.ColorRole.Highlight, '#235d58'),
            (QPalette.ColorRole.HighlightedText, '#e4edf7'),
            (QPalette.ColorRole.PlaceholderText, '#8a9bb0'),
        ):
            palette.setColor(role, QColor(self.resolve(value)))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(self.resolve('#8a9bb0')))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(self.resolve('#8a9bb0')))
        app.setPalette(palette)
        # Una sustitución por color evita reemplazos en cadena entre ambas paletas.
        stylesheet = re.sub(r'#[0-9a-fA-F]{6}', lambda match: self.resolve(match[0]), self.dark_stylesheet)
        icons = Path(__file__).resolve().parent / 'icons'
        for direction in ('up', 'down'):
            stylesheet = stylesheet.replace(f'__ARROW_{direction.upper()}__',
                                            (icons / f'chevron-{direction}-{self.mode}.svg').as_posix())
        app.setStyleSheet(stylesheet)

    def set_mode(self, mode, persist=True):
        if mode not in ('dark', 'light'):
            raise ValueError('Modo de apariencia desconocido.')
        self.mode = mode
        self.apply()
        self.changed.emit()
        if persist:
            self.save()

    def save(self):
        preferences = {}
        try:
            saved = json.loads(self.path.read_text())
            if isinstance(saved, dict):
                preferences.update(saved)
        except (OSError, ValueError):
            pass
        preferences['theme'] = self.mode
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = QSaveFile(str(self.path))
        if not target.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError(target.errorString())
        data = (json.dumps(preferences, indent=2) + '\n').encode()
        if target.write(data) != len(data):
            target.cancelWriting()
            raise OSError('No se pudo escribir la preferencia de apariencia.')
        if not target.commit():
            raise OSError(target.errorString())


def get_theme(stylesheet=''):
    app = QApplication.instance()
    if not hasattr(app, 'motorlab_theme'):
        app.motorlab_theme = ThemeManager(stylesheet)
    return app.motorlab_theme


def themed(color):
    manager = getattr(QApplication.instance(), 'motorlab_theme', None)
    return manager.resolve(color) if manager else color
