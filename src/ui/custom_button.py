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
        self._custom_premium_surface = False
        self._custom_text_shadow_color = None
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

            if getattr(self, "_custom_premium_surface", False):
                surface_rect = QRectF(rect)
                if self._pressed:
                    surface_rect.translate(0, 0.75)

                def _alpha(color: QColor, alpha: int) -> QColor:
                    next_color = QColor(color)
                    next_color.setAlpha(alpha)
                    return next_color

                top_color = _lighten(QColor(start_color), 10 if self._hovered else 5)
                bottom_color = QColor(end_color)
                base = QLinearGradient(surface_rect.left(), surface_rect.top(), surface_rect.left(), surface_rect.bottom())
                base.setColorAt(0.0, top_color)
                base.setColorAt(0.46, QColor(start_color))
                base.setColorAt(1.0, bottom_color)
                painter.setBrush(QBrush(base))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(surface_rect, radius, radius)

                side_tint = QLinearGradient(surface_rect.left(), surface_rect.center().y(), surface_rect.right(), surface_rect.center().y())
                side_tint.setColorAt(0.0, _alpha(QColor(start_color), 34 if self._hovered else 24))
                side_tint.setColorAt(0.52, QColor(255, 255, 255, 0))
                side_tint.setColorAt(1.0, _alpha(QColor(end_color), 42 if self._hovered else 30))
                painter.setBrush(QBrush(side_tint))
                painter.drawRoundedRect(surface_rect.adjusted(0.7, 0.7, -0.7, -0.7), max(0.0, radius - 0.7), max(0.0, radius - 0.7))

                top_highlight = QLinearGradient(surface_rect.left(), surface_rect.top(), surface_rect.left(), surface_rect.top() + surface_rect.height() * 0.42)
                top_highlight.setColorAt(0.0, QColor(255, 255, 255, 48 if self._hovered else 36))
                top_highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(QBrush(top_highlight))
                painter.drawRoundedRect(surface_rect.adjusted(1.0, 1.0, -1.0, -surface_rect.height() * 0.35), max(0.0, radius - 1.0), max(0.0, radius - 1.0))

                bottom_depth = QLinearGradient(surface_rect.left(), surface_rect.center().y(), surface_rect.left(), surface_rect.bottom())
                bottom_depth.setColorAt(0.0, QColor(0, 0, 0, 0))
                bottom_depth.setColorAt(1.0, QColor(0, 0, 0, 48 if self._pressed else 34))
                painter.setBrush(QBrush(bottom_depth))
                painter.drawRoundedRect(surface_rect.adjusted(1.0, surface_rect.height() * 0.36, -1.0, -1.0), max(0.0, radius - 1.0), max(0.0, radius - 1.0))

                inner_border = QPen(QColor(255, 255, 255, 28 if self._hovered else 20), 0.65)
                inner_border.setCosmetic(True)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(inner_border)
                painter.drawRoundedRect(surface_rect.adjusted(1.05, 1.05, -1.05, -1.05), max(0.0, radius - 1.05), max(0.0, radius - 1.05))

                if self._custom_border is not None:
                    border_color = QColor(self._custom_border)
                    border_grad = QLinearGradient(surface_rect.left(), surface_rect.top(), surface_rect.left(), surface_rect.bottom())
                    border_grad.setColorAt(0.0, _alpha(QColor(255, 255, 255), min(border_color.alpha() + 32, 210)))
                    border_grad.setColorAt(0.48, border_color)
                    border_grad.setColorAt(1.0, _alpha(border_color, max(12, border_color.alpha() // 2)))
                    border_pen = QPen(QBrush(border_grad), 1.0)
                    border_pen.setCosmetic(True)
                    painter.setPen(border_pen)
                    painter.drawRoundedRect(surface_rect, radius, radius)
            else:
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
        if self._custom_text_shadow_color is not None:
            painter.setPen(QColor(self._custom_text_shadow_color))
            painter.drawText(rect.adjusted(0, 1, 0, 1), Qt.AlignVCenter | Qt.AlignHCenter, self.text())
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
