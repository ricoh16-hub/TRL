
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
        radius = 14
        # --- Button background ---
        if self._custom_bg is not None:
            # Custom color (misal: warna gembok/putih)
            bg = QColor(self._custom_bg)
            if self._hovered:
                # Hover: putih → abu muda, lain → lebih terang
                if bg.red() == 255 and bg.green() == 255 and bg.blue() == 255:
                    bg = QColor(240, 245, 255)
                else:
                    bg = QColor(min(bg.red()+18,255), min(bg.green()+18,255), min(bg.blue()+18,255), bg.alpha())
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)
            # Outline tipis jika putih: gunakan hitam
            if self._custom_bg.red() == 255 and self._custom_bg.green() == 255 and self._custom_bg.blue() == 255:
                painter.setPen(QPen(QColor(0, 0, 0), 1))
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
            # Secondary style (Cancel)
            bg = QColor(60, 60, 80, 220) if not self._hovered else QColor(80, 80, 110, 230)
            painter.setBrush(bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

        # --- Draw text and icon ---
        text = self.text()
        font = QFont('SF Pro Display', 10)
        font.setBold(True)
        painter.setFont(font)
        # Pilih warna teks kontras dengan background
        if self._custom_bg is not None:
            bg = QColor(self._custom_bg)
            # Jika putih atau sangat terang, pakai teks gelap
            if bg.red() > 240 and bg.green() > 240 and bg.blue() > 240:
                color = QColor("#22304A")  # biru gelap
            else:
                color = QColor("#FFFFFF")
        elif self.primary:
            color = QColor("#FFFFFF")
        else:
            color = QColor("#FFFFFF")
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
