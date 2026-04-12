from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


class CardShimmer(QWidget):
    """Shimmer sweep animation for Card Panel, matching _GlowBar style."""
    _TICK_MS = 16
    _SWEEP_MS = 3000
    _PAUSE_MS = 1500

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(180, 210, 255, 204)
        self._radius = 12
        self._glow_height = 16
        self.setFixedHeight(self._glow_height)
        self._pos = -0.15
        self._pausing = False
        self._pause_ticks = 0
        self._step = 1.3 / (self._SWEEP_MS / self._TICK_MS)
        self._fade_alpha = 0.0
        self._fade_in = True
        self._fade_out = False
        self._fade_step = 1.0 / (0.18 * self._SWEEP_MS / self._TICK_MS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._TICK_MS)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def set_radius(self, radius: int) -> None:
        self._radius = radius
        self.update()

    def set_height(self, height: int) -> None:
        self._glow_height = height
        self.setFixedHeight(height)
        self.update()

    def stop_shimmer(self):
        self._timer.stop()
        self.hide()

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def _tick(self) -> None:
        if self._fade_in:
            self._fade_alpha += self._fade_step
            if self._fade_alpha >= 1.0:
                self._fade_alpha = 1.0
                self._fade_in = False
        if self._fade_out:
            self._fade_alpha -= self._fade_step
            if self._fade_alpha <= 0.0:
                self._fade_alpha = 0.0
                self._fade_out = False
                self._pausing = True
                self._pause_ticks = self._PAUSE_MS // self._TICK_MS
                self._pos = -0.15
        if self._pausing:
            self._pause_ticks -= 1
            if self._pause_ticks <= 0:
                self._pausing = False
                self._fade_in = True
        else:
            self._pos += self._step
            if self._pos > 0.95 and not self._fade_out:
                self._fade_out = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        radius = self._radius
        margin = radius
        if w < 2 * margin:
            margin = 0
        flat_w = w - 2 * margin
        path = QPainterPath()
        path.addRoundedRect(margin, 0, flat_w, self._glow_height, radius, radius)
        painter.setClipPath(path)
        base = QLinearGradient(margin, 0, w - margin, 0)
        dim = QColor(self._color)
        dim.setAlphaF(0.18 * self._fade_alpha)
        base.setColorAt(0.0, QColor(0, 0, 0, 0))
        base.setColorAt(0.2, QColor(0, 0, 0, 0))
        base.setColorAt(0.5, dim)
        base.setColorAt(0.8, QColor(0, 0, 0, 0))
        base.setColorAt(1.0, QColor(0, 0, 0, 0))
        for y in range(0, self._glow_height):
            alpha = max(0.0, 0.7 - y / self._glow_height)
            color = QColor(self._color)
            color.setAlphaF(dim.alphaF() * alpha)
            grad = QLinearGradient(margin, y, w - margin, y)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.5, color)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(margin, y, flat_w, 1, grad)
        shine_w = flat_w * 0.22
        cx = margin + self._pos * flat_w
        shimmer = QLinearGradient(cx - shine_w, 0, cx + shine_w, 0)
        shimmer.setColorAt(0.0, QColor(0, 0, 0, 0))
        shimmer.setColorAt(0.5, self._color)
        shimmer.setColorAt(1.0, QColor(0, 0, 0, 0))
        for y in range(0, self._glow_height):
            alpha = max(0.0, 1.0 - y / self._glow_height)
            color = QColor(self._color)
            color.setAlphaF(self._color.alphaF() * alpha * self._fade_alpha)
            grad = QLinearGradient(cx - shine_w, y, cx + shine_w, y)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.5, color)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(margin, y, flat_w, 1, grad)
        painter.end()
