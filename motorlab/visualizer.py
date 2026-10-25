"""Dibujo vectorial nativo: corte esquemático del motor y flujos de energía."""
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget
from .theme import themed

BG = '#0a111b'
CYAN = '#4ee2cd'
AMBER = '#ffba6b'
TEXT = '#e4edf7'
MUTED = '#8a9bb0'


class MotorView(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.visual_angle = 0.0
        self.setMinimumSize(410, 370)
        self.setToolTip('Corte transversal esquemático de un motor DC. El giro visual está ralentizado para observar el rotor.')
        controller.timer.timeout.connect(self.animate)

    def animate(self):
        if self.controller.running:
            # Giro didáctico limitado: no es una representación estroboscópica de RPM reales.
            self.visual_angle += min(5.5, self.controller.motor.omega * 0.018) * 0.033
        self.update()

    def text(self, painter, rect, text, size=12, color=TEXT, bold=False, align=Qt.AlignmentFlag.AlignCenter):
        painter.setPen(QColor(themed(color)))
        font = QFont('DejaVu Sans', size)
        font.setBold(bold)
        painter.setFont(font)
        painter.drawText(rect, align, text)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(themed(BG)))
        scale = min(self.width() / 640, self.height() / 520)
        p.translate((self.width() - 640 * scale) / 2, (self.height() - 520 * scale) / 2)
        p.scale(scale, scale)
        # Retícula de ingeniería, sutil y estable al redimensionar.
        p.setPen(QPen(QColor(themed('#142231')), 1))
        for x in range(0, 641, 32):
            p.drawLine(x, 0, x, 520)
        for y in range(0, 521, 32):
            p.drawLine(0, y, 640, y)
        self.text(p, QRectF(20, 15, 340, 25), '01 / CORTE ELECTROMECÁNICO', 10, MUTED,
                  align=Qt.AlignmentFlag.AlignLeft)
        motor = self.controller.motor
        heat = min(1.0, max(0, (motor.temperature - 25) / 80))
        glow = QRadialGradient(320, 245, 230)
        glow.setColorAt(0, QColor(30 + int(90*heat), 80, 80, 75))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(320, 245), 235, 235)
        # Carcasa y fijaciones.
        shell = QLinearGradient(145, 65, 485, 425)
        shell.setColorAt(0, QColor('#354553'))
        shell.setColorAt(.45, QColor('#152130'))
        shell.setColorAt(1, QColor('#293a46'))
        p.setBrush(shell)
        p.setPen(QPen(QColor('#4c6270'), 2))
        p.drawEllipse(QPointF(320, 245), 181, 181)
        p.setBrush(QColor('#0b141d'))
        p.setPen(QPen(QColor('#526974'), 1))
        p.drawEllipse(QPointF(320, 245), 159, 159)
        for degree in (45, 135, 225, 315):
            a = math.radians(degree)
            cx, cy = 320 + 170*math.cos(a), 245 + 170*math.sin(a)
            p.setBrush(QColor('#718391'))
            p.drawEllipse(QPointF(cx, cy), 6, 6)
            p.setPen(QPen(QColor('#0a111b'), 2))
            p.drawLine(QPointF(cx-3, cy+3), QPointF(cx+3, cy-3))
        # Imanes permanentes: norte y sur.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor('#368d93'), 24, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(176, 101, 288, 288), 110*16, 140*16)
        p.setPen(QPen(QColor('#a16650'), 24, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(176, 101, 288, 288), -70*16, 140*16)
        self.text(p, QRectF(151, 229, 48, 30), 'N', 15, '#f6f9fc', True)
        self.text(p, QRectF(442, 229, 48, 30), 'S', 15, '#f6f9fc', True)
        # Líneas de flujo magnético.
        p.setPen(QPen(QColor('#274648'), 1, Qt.PenStyle.DashLine))
        for y in (181, 213, 277, 309):
            p.drawLine(208, y, 432, y)
        # Rotor con doce ranuras de cobre, animado.
        p.save()
        p.translate(320, 245)
        p.rotate(math.degrees(self.visual_angle))
        rotor = QRadialGradient(-30, -35, 135)
        rotor.setColorAt(0, QColor('#43535f'))
        rotor.setColorAt(1, QColor('#1c2a35'))
        p.setBrush(rotor)
        p.setPen(QPen(QColor('#81949e'), 2))
        p.drawEllipse(QPointF(0, 0), 108, 108)
        for n in range(12):
            p.save()
            p.rotate(n * 30)
            winding = QLinearGradient(0, -103, 0, -57)
            winding.setColorAt(0, QColor('#e6ab75'))
            winding.setColorAt(1, QColor('#84492f'))
            p.setBrush(winding)
            p.setPen(QPen(QColor('#462f28'), 2))
            p.drawRoundedRect(QRectF(-11, -104, 22, 42), 5, 5)
            p.setPen(QPen(QColor('#623e2b'), 1))
            for line in range(5):
                p.drawLine(-9, -96+line*6, 9, -96+line*6)
            p.restore()
        p.setBrush(QColor('#9b6f4e'))
        p.setPen(QPen(QColor('#d5ac80'), 2))
        p.drawEllipse(QPointF(0, 0), 42, 42)
        for n in range(12):
            a = n*math.tau/12
            p.setPen(QPen(QColor('#17232c'), 2))
            p.drawLine(QPointF(26*math.cos(a), 26*math.sin(a)), QPointF(41*math.cos(a), 41*math.sin(a)))
        p.setBrush(QColor('#a8bac5'))
        p.setPen(QPen(QColor('#e3e9ee'), 2))
        p.drawEllipse(QPointF(0, 0), 24, 24)
        p.setBrush(QColor('#233541'))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-5, -22, 10, 15), 2, 2)
        p.restore()
        # Escobillas y alimentación: conexiones visibles, etiquetas fijas.
        p.setBrush(QColor('#536774'))
        p.setPen(QPen(QColor('#9cb0ba'), 1))
        p.drawRoundedRect(QRectF(303, 190, 34, 20), 3, 3)
        p.drawRoundedRect(QRectF(303, 280, 34, 20), 3, 3)
        p.setPen(QPen(QColor(CYAN), 2))
        p.drawLine(320, 190, 320, 151)
        p.drawLine(320, 151, 263, 151)
        p.setPen(QPen(QColor(AMBER), 2))
        p.drawLine(320, 300, 320, 339)
        p.drawLine(320, 339, 377, 339)
        # Llamadas.
        p.setPen(QPen(QColor('#4c6270'), 1))
        p.drawLine(443, 145, 505, 100)
        p.drawLine(505, 100, 613, 100)
        self.text(p, QRectF(496, 76, 125, 22), 'ESTATOR', 10, MUTED)
        p.drawLine(421, 312, 512, 364)
        p.drawLine(512, 364, 617, 364)
        self.text(p, QRectF(503, 368, 120, 25), 'BOBINADO', 10, MUTED)
        p.drawLine(213, 315, 124, 364)
        p.drawLine(26, 364, 124, 364)
        self.text(p, QRectF(22, 368, 108, 25), 'ROTOR', 10, MUTED)
        self.text(p, QRectF(110, 434, 420, 32), f'{motor.snapshot()["rpm"]:,.0f}  RPM', 23, CYAN, True)
        self.text(p, QRectF(90, 478, 460, 22), 'VISTA DIDÁCTICA · GIRO RALENTIZADO · MODELO DC', 9, MUTED)
        p.end()
