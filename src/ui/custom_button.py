
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
        # Tidak menggambar background apapun (benar-benar transparan)

        # --- Draw text and icon ---
        text = self.text()
        font = QFont('SF Pro Display', 10)
        font.setBold(True)
        painter.setFont(font)
        color = QColor("#22304A")  # Gunakan warna teks gelap agar kontras di background transparan
        painter.setPen(color)
        # Center text horizontally and vertically
        text_rect = rect
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignHCenter, text)
        if self._icon:
            icon_rect = QRectF(rect.right() - 24 - self._icon_size.width(),
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
