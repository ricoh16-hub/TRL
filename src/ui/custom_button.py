from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QBrush, QPen, QFont
from PySide6.QtCore import Qt, QRectF

class CustomButton(QPushButton):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        # Gradient body seperti body gembok login.py
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, QColor(255, 255, 255))
        grad.setColorAt(1.0, QColor(230, 230, 230))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawRoundedRect(rect, 12, 12)
        # Highlight garis putih di atas/kiri
        painter.setPen(QPen(QColor(255, 255, 255, 100), 2))
        painter.drawLine(rect.left()+3, rect.top()+3, rect.right()-3, rect.top()+3)
        # Teks tombol
        painter.setPen(QColor(34, 42, 54))
        font = QFont('SF Pro Display', 13, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())
