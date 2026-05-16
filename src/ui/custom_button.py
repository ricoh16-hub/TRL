from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QPushButton


class CustomButton(QPushButton):
    def sizeHint(self):
        return QSize(100, 5)

    def setStyleSheet(self, style):
        # Keep painting fully controlled by this widget.
        super().setStyleSheet("")

    def __init__(self, text, *, primary=False, icon: QIcon = None, icon_size: QSize = QSize(20, 20), parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self._hovered = False
        self._pressed = False
        self._icon = icon
        self._icon_size = icon_size
        self._custom_bg = None
        self._custom_hover_bg = None
        self._custom_gradient = None
        self._custom_hover_gradient = None
        self._custom_border = None
        self._custom_text_color = None
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent; font-weight: 600; font-family: 'SF Pro Display', Arial, sans-serif;")
        self.setMinimumHeight(5)
        self.setMaximumHeight(5)
        from PySide6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._custom_radius = 10.5
        self.setContentsMargins(0, 0, 0, 0)
        self.setMouseTracking(True)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self._hovered = True
            self.update()
        elif event.type() == QEvent.Leave:
            self._hovered = False
            self.update()
        elif event.type() == QEvent.MouseButtonPress:
            self._pressed = True
            self.update()
        elif event.type() == QEvent.MouseButtonRelease:
            self._pressed = False
            self.update()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = getattr(self, "_custom_radius", 14)

        def _lighten(color: QColor, amount: int = 18) -> QColor:
            return QColor(
                min(color.red() + amount, 255),
                min(color.green() + amount, 255),
                min(color.blue() + amount, 255),
                color.alpha(),
            )

        if self._custom_gradient is not None:
            start_color, end_color = self._custom_gradient
            if self._hovered and self._custom_hover_gradient is not None:
                start_color, end_color = self._custom_hover_gradient

            grad = QLinearGradient(rect.topLeft(), rect.topRight())
            grad.setColorAt(0.0, QColor(start_color))
            grad.setColorAt(1.0, QColor(end_color))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)
            if self._custom_border is not None:
                painter.setPen(QPen(QColor(self._custom_border), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect, radius, radius)
        elif self._custom_bg is not None:
            bg = QColor(self._custom_bg)
            if self._hovered and self._custom_hover_bg is not None:
                bg = QColor(self._custom_hover_bg)
            elif self._hovered:
                bg = _lighten(bg)

            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)
            if self._custom_border is not None:
                painter.setPen(QPen(QColor(self._custom_border), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect, radius, radius)
            elif self._custom_bg.red() > 200 and self._custom_bg.green() > 200 and self._custom_bg.blue() > 200:
                painter.setPen(QPen(QColor(180, 180, 180), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect, radius, radius)
        elif self.primary:
            grad = QLinearGradient(rect.topLeft(), rect.topRight())
            if self._hovered:
                grad.setColorAt(0.0, QColor("#4F98F7"))
                grad.setColorAt(1.0, QColor("#7EC8FA"))
            else:
                grad.setColorAt(0.0, QColor("#3B82F6"))
                grad.setColorAt(1.0, QColor("#60A5FA"))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)
        else:
            bg = QColor(60, 60, 80, 220) if not self._hovered else QColor(80, 80, 110, 230)
            painter.setBrush(bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

        font = QFont("SF Pro Display", 10)
        font.setBold(True)
        painter.setFont(font)
        if self._custom_text_color is not None:
            color = QColor(self._custom_text_color)
        elif self._custom_bg is not None:
            bg = QColor(self._custom_bg)
            color = QColor("#333333") if bg.red() > 200 and bg.green() > 200 and bg.blue() > 200 else QColor("#FFFFFF")
        else:
            color = QColor("#FFFFFF")
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignHCenter, self.text())
        if self._icon:
            icon_rect = QRectF(
                rect.right() - 24 - self._icon_size.width(),
                rect.center().y() - self._icon_size.height() / 2,
                self._icon_size.width(),
                self._icon_size.height(),
            )
            self._icon.paint(painter, icon_rect.toRect(), Qt.AlignCenter)

    def setPrimary(self, value: bool):
        self.primary = value
        self.update()

    def setButtonIcon(self, icon: QIcon, size: QSize = QSize(20, 20)):
        self._icon = icon
        self._icon_size = size
        self.update()
