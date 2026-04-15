
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QBrush, QPen, QFont, QIcon
from PySide6.QtCore import Qt, QRectF, QSize, QEvent

class CustomButton(QPushButton):
    def __init__(self, text, *, primary=False, icon: QIcon = None, icon_size: QSize = QSize(20, 20), parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self._hovered = False
        self._pressed = False
        self._icon = icon
        self._icon_size = icon_size
        self._custom_bg = None  # QColor or None
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent; font-weight: 600; font-family: 'SF Pro Display', Arial, sans-serif;")
        self.setMinimumHeight(44)
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
        radius = 12
        # Primary style
        if self._custom_bg is not None:
            # Gunakan warna custom (misal: warna gembok)
            painter.setBrush(QBrush(self._custom_bg))
            painter.setPen(Qt.NoPen)
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
            # Shadow
            if self._hovered or self._pressed:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(80, 180, 255, 60))
                painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), radius+2, radius+2)
            # Glow effect
            if self._hovered:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(80, 180, 255, 40))
                painter.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), radius+4, radius+4)
        else:
            # Secondary style
            bg = QColor("#2A2F3A") if not self._hovered else QColor("#353B47")
            painter.setBrush(bg)
            painter.setPen(QPen(QColor(255,255,255,50), 1))
            painter.drawRoundedRect(rect, radius, radius)

        # Active (pressed) effect
        if self._pressed:
            painter.save()
            painter.setOpacity(0.92)
            painter.scale(0.97, 0.97)
            painter.restore()

        # Draw text and icon
        text = self.text()
        font = QFont('SF Pro Display', 13, QFont.DemiBold)
        painter.setFont(font)
        color = QColor("#FFFFFF") if self.primary else QColor("#E6EAF3")
        painter.setPen(color)
        padding_x = 24
        icon_space = self._icon_size.width() + 8 if self._icon else 0
        # Center text and icon
        text_rect = rect.adjusted(padding_x, 0, -padding_x - icon_space, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        if self._icon:
            icon_rect = QRectF(rect.right() - padding_x - self._icon_size.width(),
                               rect.center().y() - self._icon_size.height()/2,
                               self._icon_size.width(), self._icon_size.height())
            self._icon.paint(painter, icon_rect.toRect(), Qt.AlignCenter)

    def setPrimary(self, value: bool):
        self.primary = value
        self.update()

    def setButtonIcon(self, icon: QIcon, size: QSize = QSize(20, 20)):
        self._icon = icon
        self._icon_size = size
        self.update()
