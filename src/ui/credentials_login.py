import logging
import os
from typing import Optional

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPointF, QPropertyAnimation, QSize, Qt, QRectF, QTimer
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QBrush,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QToolButton, QVBoxLayout, QWidget
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect

logger = logging.getLogger(__name__)
CREDENTIALS_FONT_STACK = "'Segoe UI', 'Arial', sans-serif"

try:
    from ui.custom_button import CustomButton
except ImportError:
    from src.ui.custom_button import CustomButton

try:
    from ui.flow_auth import authenticate_credentials_step
except ImportError:
    from src.ui.flow_auth import authenticate_credentials_step

try:
    from database.models import User
except ImportError:
    from src.database.models import User


class PremiumCredentialsDialog(QDialog):
    """Credentials dialog background painted with the same layered glass language as lock.py."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._background_corner_radius = 22.0
        self._background_charging = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

    def set_charging_background(self, charging: bool) -> None:
        charging = bool(charging)
        if self._background_charging == charging:
            return
        self._background_charging = charging
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        border_inset = 1.0
        rect = QRectF(
            border_inset,
            border_inset,
            self.width() - (border_inset * 2.0),
            self.height() - (border_inset * 2.0),
        )
        radius = max(0.0, self._background_corner_radius - border_inset)
        charging = bool(getattr(self, "_background_charging", False))

        if charging:
            top_color = QColor(18, 30, 43)
            mid_color = QColor(31, 47, 64)
            bottom_color = QColor(20, 36, 55)
            accent_top = QColor(103, 224, 255, 34)
            accent_bottom = QColor(55, 138, 238, 18)
            focus_color = QColor(103, 224, 255, 30)
            inner_highlight = QColor(232, 250, 255, 34)
            lower_shadow = QColor(4, 16, 30, 44)
            lower_accent_color = QColor(55, 138, 238, 16)
            edge_shadow_color = QColor(2, 12, 24, 26)
            inner_border_color = QColor(232, 250, 255, 28)
            border_top_color = QColor(232, 250, 255, 54)
            border_mid_color = QColor(103, 224, 255, 64)
            border_bottom_color = QColor(55, 138, 238, 26)
        else:
            top_color = QColor(26, 32, 41)
            mid_color = QColor(41, 49, 60)
            bottom_color = QColor(31, 39, 50)
            accent_top = QColor(255, 255, 255, 18)
            accent_bottom = QColor(205, 216, 228, 10)
            focus_color = QColor(255, 255, 255, 20)
            inner_highlight = QColor(255, 255, 255, 27)
            lower_shadow = QColor(0, 0, 0, 42)
            lower_accent_color = QColor(205, 216, 228, 9)
            edge_shadow_color = QColor(0, 0, 0, 22)
            inner_border_color = QColor(255, 255, 255, 24)
            border_top_color = QColor(255, 255, 255, 44)
            border_mid_color = QColor(255, 255, 255, 45)
            border_bottom_color = QColor(205, 216, 228, 20)

        background = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        background.setColorAt(0.0, top_color)
        background.setColorAt(0.48, mid_color)
        background.setColorAt(1.0, bottom_color)

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(background))
        painter.drawPath(path)

        painter.setClipPath(path)
        accent = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        accent.setColorAt(0.0, accent_top)
        accent.setColorAt(
            0.58,
            QColor(accent_top.red(), accent_top.green(), accent_top.blue(), max(4, accent_top.alpha() // 3)),
        )
        accent.setColorAt(1.0, accent_bottom)
        painter.setBrush(QBrush(accent))
        painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

        focus_glow = QRadialGradient(QPointF(rect.center().x(), rect.top() + 172.0), 190.0)
        focus_glow.setColorAt(0.0, focus_color)
        focus_glow.setColorAt(
            0.46,
            QColor(focus_color.red(), focus_color.green(), focus_color.blue(), max(3, focus_color.alpha() // 3)),
        )
        focus_glow.setColorAt(1.0, QColor(focus_color.red(), focus_color.green(), focus_color.blue(), 0))
        painter.setBrush(QBrush(focus_glow))
        painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

        top_highlight = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + 18.0)
        top_highlight.setColorAt(0.0, inner_highlight)
        top_highlight.setColorAt(1.0, QColor(inner_highlight.red(), inner_highlight.green(), inner_highlight.blue(), 0))
        painter.setBrush(QBrush(top_highlight))
        painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

        lower_accent = QRadialGradient(QPointF(rect.center().x(), rect.bottom() - 4.0), 118.0)
        lower_accent.setColorAt(0.0, lower_accent_color)
        lower_accent.setColorAt(
            0.52,
            QColor(
                lower_accent_color.red(),
                lower_accent_color.green(),
                lower_accent_color.blue(),
                max(2, lower_accent_color.alpha() // 3),
            ),
        )
        lower_accent.setColorAt(
            1.0,
            QColor(lower_accent_color.red(), lower_accent_color.green(), lower_accent_color.blue(), 0),
        )
        painter.setBrush(QBrush(lower_accent))
        painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

        edge_shading = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        edge_shading.setColorAt(0.0, edge_shadow_color)
        edge_shading.setColorAt(0.18, QColor(edge_shadow_color.red(), edge_shadow_color.green(), edge_shadow_color.blue(), 0))
        edge_shading.setColorAt(0.82, QColor(edge_shadow_color.red(), edge_shadow_color.green(), edge_shadow_color.blue(), 0))
        edge_shading.setColorAt(1.0, edge_shadow_color)
        painter.setBrush(QBrush(edge_shading))
        painter.drawRoundedRect(rect.adjusted(1.1, 1.1, -1.1, -1.1), radius - 1.1, radius - 1.1)

        bottom_depth = QLinearGradient(rect.left(), rect.bottom() - 30.0, rect.left(), rect.bottom())
        bottom_depth.setColorAt(0.0, QColor(lower_shadow.red(), lower_shadow.green(), lower_shadow.blue(), 0))
        bottom_depth.setColorAt(1.0, lower_shadow)
        painter.setBrush(QBrush(bottom_depth))
        painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

        painter.setClipping(False)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inner_rect = rect.adjusted(1.05, 1.05, -1.05, -1.05)
        inner_pen = QPen(inner_border_color, 0.65)
        inner_pen.setCosmetic(True)
        painter.setPen(inner_pen)
        painter.drawRoundedRect(inner_rect, radius - 1.05, radius - 1.05)

        border_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        border_gradient.setColorAt(0.0, border_top_color)
        border_gradient.setColorAt(0.46, border_mid_color)
        border_gradient.setColorAt(1.0, border_bottom_color)
        border_pen = QPen(QBrush(border_gradient), 1.0)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()


def _paint_lock_reference_background(
    painter: QPainter,
    event: QPaintEvent,
    width: int,
    height: int,
    corner_radius: float,
    charging: bool,
    focus_y: float = 42.0,
    focus_radius: float = 178.0,
) -> None:
    """Paint a rounded glass surface using the same layer order as lock.py."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    border_inset = 1.0
    rect = QRectF(
        border_inset,
        border_inset,
        width - (border_inset * 2.0),
        height - (border_inset * 2.0),
    )
    radius = max(0.0, corner_radius - border_inset)

    if charging:
        top_color = QColor(18, 30, 43)
        mid_color = QColor(31, 47, 64)
        bottom_color = QColor(20, 36, 55)
        accent_top = QColor(103, 224, 255, 34)
        accent_bottom = QColor(55, 138, 238, 18)
        border_color = QColor(103, 224, 255, 64)
        inner_highlight = QColor(232, 250, 255, 34)
        lower_shadow = QColor(4, 16, 30, 44)
        focus_color = QColor(103, 224, 255, 30)
        inner_border_color = QColor(232, 250, 255, 28)
        lower_accent_color = QColor(55, 138, 238, 16)
        edge_shadow_color = QColor(2, 12, 24, 26)
        border_top_color = QColor(232, 250, 255, 54)
        border_bottom_color = QColor(55, 138, 238, 26)
    else:
        top_color = QColor(26, 32, 41)
        mid_color = QColor(41, 49, 60)
        bottom_color = QColor(31, 39, 50)
        accent_top = QColor(255, 255, 255, 18)
        accent_bottom = QColor(205, 216, 228, 10)
        border_color = QColor(255, 255, 255, 45)
        inner_highlight = QColor(255, 255, 255, 27)
        lower_shadow = QColor(0, 0, 0, 42)
        focus_color = QColor(255, 255, 255, 20)
        inner_border_color = QColor(255, 255, 255, 24)
        lower_accent_color = QColor(205, 216, 228, 9)
        edge_shadow_color = QColor(0, 0, 0, 22)
        border_top_color = QColor(255, 255, 255, 44)
        border_bottom_color = QColor(205, 216, 228, 20)

    background = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    background.setColorAt(0.0, top_color)
    background.setColorAt(0.48, mid_color)
    background.setColorAt(1.0, bottom_color)

    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(background))
    painter.drawPath(path)

    painter.setClipPath(path)
    accent = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
    accent.setColorAt(0.0, accent_top)
    accent.setColorAt(0.58, QColor(accent_top.red(), accent_top.green(), accent_top.blue(), max(4, accent_top.alpha() // 3)))
    accent.setColorAt(1.0, accent_bottom)
    painter.setBrush(QBrush(accent))
    painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

    focus_glow = QRadialGradient(QPointF(rect.center().x(), rect.top() + focus_y), focus_radius)
    focus_glow.setColorAt(0.0, focus_color)
    focus_glow.setColorAt(0.42, QColor(focus_color.red(), focus_color.green(), focus_color.blue(), max(3, focus_color.alpha() // 3)))
    focus_glow.setColorAt(1.0, QColor(focus_color.red(), focus_color.green(), focus_color.blue(), 0))
    painter.setBrush(QBrush(focus_glow))
    painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

    top_highlight = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + 18.0)
    top_highlight.setColorAt(0.0, inner_highlight)
    top_highlight.setColorAt(1.0, QColor(inner_highlight.red(), inner_highlight.green(), inner_highlight.blue(), 0))
    painter.setBrush(QBrush(top_highlight))
    painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

    lower_accent = QRadialGradient(QPointF(rect.center().x(), rect.bottom() - 4.0), 118.0)
    lower_accent.setColorAt(0.0, lower_accent_color)
    lower_accent.setColorAt(
        0.52,
        QColor(lower_accent_color.red(), lower_accent_color.green(), lower_accent_color.blue(), max(2, lower_accent_color.alpha() // 3)),
    )
    lower_accent.setColorAt(1.0, QColor(lower_accent_color.red(), lower_accent_color.green(), lower_accent_color.blue(), 0))
    painter.setBrush(QBrush(lower_accent))
    painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

    edge_shading = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    edge_shading.setColorAt(0.0, edge_shadow_color)
    edge_shading.setColorAt(0.18, QColor(edge_shadow_color.red(), edge_shadow_color.green(), edge_shadow_color.blue(), 0))
    edge_shading.setColorAt(0.82, QColor(edge_shadow_color.red(), edge_shadow_color.green(), edge_shadow_color.blue(), 0))
    edge_shading.setColorAt(1.0, edge_shadow_color)
    painter.setBrush(QBrush(edge_shading))
    painter.drawRoundedRect(rect.adjusted(1.1, 1.1, -1.1, -1.1), radius - 1.1, radius - 1.1)

    bottom_depth = QLinearGradient(rect.left(), rect.bottom() - 30.0, rect.left(), rect.bottom())
    bottom_depth.setColorAt(0.0, QColor(lower_shadow.red(), lower_shadow.green(), lower_shadow.blue(), 0))
    bottom_depth.setColorAt(1.0, lower_shadow)
    painter.setBrush(QBrush(bottom_depth))
    painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

    painter.setClipping(False)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inner_rect = rect.adjusted(1.05, 1.05, -1.05, -1.05)
    inner_pen = QPen(inner_border_color, 0.65)
    inner_pen.setCosmetic(True)
    painter.setPen(inner_pen)
    painter.drawRoundedRect(inner_rect, radius - 1.05, radius - 1.05)

    border_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    border_gradient.setColorAt(0.0, border_top_color)
    border_gradient.setColorAt(0.46, border_color)
    border_gradient.setColorAt(1.0, border_bottom_color)
    border_pen = QPen(QBrush(border_gradient), 1.0)
    border_pen.setCosmetic(True)
    painter.setPen(border_pen)
    painter.drawRoundedRect(rect, radius, radius)


class LockReferenceWarningPanel(QFrame):
    """Warning panel painted with the same main-form method as lock.py."""

    def __init__(self, charging: bool, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._charging = bool(charging)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        _paint_lock_reference_background(
            painter,
            event,
            self.width(),
            self.height(),
            18.0,
            self._charging,
            focus_y=42.0,
            focus_radius=150.0,
        )
        painter.end()


class LockReferenceCardPanel(QFrame):
    """Credentials card surface using the lock.py layered glass method."""

    def __init__(self, charging: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._charging = bool(charging)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        _paint_lock_reference_background(
            painter,
            event,
            self.width(),
            self.height(),
            19.0,
            self._charging,
            focus_y=54.0,
            focus_radius=172.0,
        )
        painter.end()


def _paint_credentials_inline_surface(
    painter: QPainter,
    event: QPaintEvent,
    width: int,
    height: int,
    radius: float,
    charging: bool,
    focused: bool = False,
    compact: bool = False,
) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    border_inset = 0.75
    rect = QRectF(
        border_inset,
        border_inset,
        width - (border_inset * 2.0),
        height - (border_inset * 2.0),
    )
    draw_radius = max(0.0, radius - border_inset)

    if charging:
        top_color = QColor(27, 45, 60, 212 if focused else 194)
        mid_color = QColor(22, 55, 75, 218 if focused else 198)
        bottom_color = QColor(17, 40, 58, 224 if focused else 202)
        accent_color = QColor(103, 224, 255, 36 if focused else 22)
        top_highlight_color = QColor(232, 250, 255, 48 if focused else 32)
        bottom_depth_color = QColor(2, 12, 24, 70 if focused else 52)
        inner_border_color = QColor(232, 250, 255, 38 if focused else 24)
        border_top_color = QColor(232, 250, 255, 132 if focused else 82)
        border_mid_color = QColor(103, 224, 255, 118 if focused else 72)
        border_bottom_color = QColor(55, 138, 238, 66 if focused else 40)
    else:
        top_color = QColor(38, 47, 59, 210 if focused else 188)
        mid_color = QColor(31, 39, 51, 214 if focused else 194)
        bottom_color = QColor(21, 29, 40, 222 if focused else 198)
        accent_color = QColor(255, 255, 255, 26 if focused else 14)
        top_highlight_color = QColor(255, 255, 255, 44 if focused else 28)
        bottom_depth_color = QColor(0, 0, 0, 66 if focused else 42)
        inner_border_color = QColor(255, 255, 255, 32 if focused else 20)
        border_top_color = QColor(255, 255, 255, 118 if focused else 70)
        border_mid_color = QColor(255, 255, 255, 88 if focused else 44)
        border_bottom_color = QColor(205, 216, 228, 48 if focused else 24)

    if compact:
        top_color.setAlpha(max(0, top_color.alpha() - 18))
        mid_color.setAlpha(max(0, mid_color.alpha() - 16))
        bottom_color.setAlpha(max(0, bottom_color.alpha() - 14))
        accent_color.setAlpha(max(0, accent_color.alpha() - 6))

    path = QPainterPath()
    path.addRoundedRect(rect, draw_radius, draw_radius)

    background = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    background.setColorAt(0.0, top_color)
    background.setColorAt(0.48, mid_color)
    background.setColorAt(1.0, bottom_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(background))
    painter.drawPath(path)

    painter.setClipPath(path)

    top_highlight = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + max(12.0, rect.height() * 0.42))
    top_highlight.setColorAt(0.0, top_highlight_color)
    top_highlight.setColorAt(1.0, QColor(top_highlight_color.red(), top_highlight_color.green(), top_highlight_color.blue(), 0))
    painter.setBrush(QBrush(top_highlight))
    painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -rect.height() * 0.34), draw_radius - 1.0, draw_radius - 1.0)

    focus_glow = QRadialGradient(QPointF(rect.center().x(), rect.top() + rect.height() * 0.38), rect.width() * 0.64)
    focus_glow.setColorAt(0.0, accent_color)
    focus_glow.setColorAt(
        0.52,
        QColor(accent_color.red(), accent_color.green(), accent_color.blue(), max(2, accent_color.alpha() // 3)),
    )
    focus_glow.setColorAt(1.0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 0))
    painter.setBrush(QBrush(focus_glow))
    painter.drawRoundedRect(rect.adjusted(0.8, 0.8, -0.8, -0.8), draw_radius - 0.8, draw_radius - 0.8)

    bottom_depth = QLinearGradient(rect.left(), rect.center().y(), rect.left(), rect.bottom())
    bottom_depth.setColorAt(0.0, QColor(bottom_depth_color.red(), bottom_depth_color.green(), bottom_depth_color.blue(), 0))
    bottom_depth.setColorAt(1.0, bottom_depth_color)
    painter.setBrush(QBrush(bottom_depth))
    painter.drawRoundedRect(rect.adjusted(1.0, rect.height() * 0.36, -1.0, -1.0), draw_radius - 1.0, draw_radius - 1.0)

    painter.setClipping(False)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inner_pen = QPen(inner_border_color, 0.65)
    inner_pen.setCosmetic(True)
    painter.setPen(inner_pen)
    painter.drawRoundedRect(rect.adjusted(1.05, 1.05, -1.05, -1.05), draw_radius - 1.05, draw_radius - 1.05)

    border_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    border_gradient.setColorAt(0.0, border_top_color)
    border_gradient.setColorAt(0.48, border_mid_color)
    border_gradient.setColorAt(1.0, border_bottom_color)
    border_pen = QPen(QBrush(border_gradient), 1.0)
    border_pen.setCosmetic(True)
    painter.setPen(border_pen)
    painter.drawRoundedRect(rect, draw_radius, draw_radius)


class CredentialsGlassInputRow(QFrame):
    """Input row surface with the same glass/depth language as the credentials card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._charging = False
        self._focused = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self.update()

    def set_focused(self, focused: bool) -> None:
        focused = bool(focused)
        if self._focused == focused:
            return
        self._focused = focused
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        _paint_credentials_inline_surface(
            painter,
            event,
            self.width(),
            self.height(),
            12.0,
            self._charging,
            self._focused,
        )
        painter.end()


class CredentialsGlassStatusChip(QFrame):
    """Compact status surface matched to the input rows."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._charging = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        _paint_credentials_inline_surface(
            painter,
            event,
            self.width(),
            self.height(),
            11.0,
            self._charging,
            False,
            compact=True,
        )
        painter.end()


class CredentialsInputFocusFilter(QObject):
    def __init__(self, row: QFrame) -> None:
        super().__init__(row)
        self._row = row

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            focused = event.type() == QEvent.Type.FocusIn
            charging = bool(self._row.property("charging"))
            self._row.setProperty("focused", focused)
            set_focused = getattr(self._row, "set_focused", None)
            if callable(set_focused):
                set_focused(focused)
            effect = self._row.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setBlurRadius((18 if focused else 13) if charging else (15 if focused else 11))
                effect.setOffset(0, 4 if focused else 3)
                if charging:
                    effect.setColor(QColor(20, 126, 190, 86) if focused else QColor(3, 18, 36, 74))
                else:
                    effect.setColor(QColor(255, 255, 255, 54) if focused else QColor(0, 0, 0, 58))
            self._row.style().unpolish(self._row)
            self._row.style().polish(self._row)
            self._row.update()
        return super().eventFilter(watched, event)


# Modern stroke-only eye icon matching the field icon language.
def _draw_eye_icon(
    size: int = 24,
    color: QColor = QColor(244, 248, 255),
    crossed: bool = False,
) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    outline_color = QColor(color)
    outline_color.setAlpha(232)
    detail_color = QColor(color)
    detail_color.setAlpha(244)

    center = QPointF(size / 2, size / 2)

    if crossed:
        lid_color = QColor(color)
        lid_color.setAlpha(228)
        lid_gradient = QLinearGradient(size * 0.18, size * 0.49, size * 0.82, size * 0.49)
        lid_edge = QColor(lid_color)
        lid_edge.setAlpha(176)
        lid_core = QColor(color)
        lid_core.setAlpha(242)
        lid_gradient.setColorAt(0.0, lid_edge)
        lid_gradient.setColorAt(0.50, lid_core)
        lid_gradient.setColorAt(1.0, lid_edge)
        lid_pen = QPen(QBrush(lid_gradient), 1.42)
        lid_pen.setCosmetic(True)
        lid_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        lid_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(lid_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        lid = QPainterPath()
        lid.moveTo(size * 0.18, size * 0.49)
        lid.cubicTo(size * 0.34, size * 0.66, size * 0.66, size * 0.66, size * 0.82, size * 0.49)
        painter.drawPath(lid)

        lash_gradient = QLinearGradient(size * 0.25, size * 0.59, size * 0.75, size * 0.80)
        lash_edge = QColor(color)
        lash_edge.setAlpha(108)
        lash_core = QColor(color)
        lash_core.setAlpha(168)
        lash_gradient.setColorAt(0.0, lash_edge)
        lash_gradient.setColorAt(0.50, lash_core)
        lash_gradient.setColorAt(1.0, lash_edge)
        lash_pen = QPen(QBrush(lash_gradient), 0.54)
        lash_pen.setCosmetic(True)
        lash_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        lash_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(lash_pen)
        left_lash = QPainterPath()
        left_lash.moveTo(size * 0.34, size * 0.59)
        left_lash.cubicTo(size * 0.30, size * 0.65, size * 0.28, size * 0.70, size * 0.25, size * 0.76)
        painter.drawPath(left_lash)
        center_lash = QPainterPath()
        center_lash.moveTo(size * 0.50, size * 0.64)
        center_lash.cubicTo(size * 0.50, size * 0.69, size * 0.50, size * 0.74, size * 0.50, size * 0.80)
        painter.drawPath(center_lash)
        right_lash = QPainterPath()
        right_lash.moveTo(size * 0.66, size * 0.59)
        right_lash.cubicTo(size * 0.70, size * 0.65, size * 0.72, size * 0.70, size * 0.75, size * 0.76)
        painter.drawPath(right_lash)
        painter.end()
        return pixmap

    outline_pen = QPen(outline_color, 1.5)
    outline_pen.setCosmetic(True)
    outline_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(outline_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    margin = size * 0.08
    top_curve_y = size * 0.16
    bottom_curve_y = size * 0.84
    path.moveTo(margin, center.y())
    path.cubicTo(size * 0.26, top_curve_y, size * 0.74, top_curve_y, size - margin, center.y())
    path.cubicTo(size * 0.74, bottom_curve_y, size * 0.26, bottom_curve_y, margin, center.y())
    painter.drawPath(path)

    iris_color = QColor(color)
    iris_color.setAlpha(214)
    iris_pen = QPen(iris_color, 1.28)
    iris_pen.setCosmetic(True)
    iris_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    iris_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    iris_radius = size * 0.18
    painter.setPen(iris_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(
        QRectF(
            center.x() - iris_radius,
            center.y() - iris_radius,
            iris_radius * 2,
            iris_radius * 2,
        )
    )
    pupil_radius = size * 0.075
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(detail_color))
    painter.drawEllipse(
        QRectF(
            center.x() - pupil_radius,
            center.y() - pupil_radius,
            pupil_radius * 2,
            pupil_radius * 2,
        )
    )
    sparkle_color = QColor(255, 255, 255, 216)
    sparkle_radius = max(0.75, size * 0.035)
    sparkle_center = QPointF(center.x() - size * 0.055, center.y() - size * 0.060)
    painter.setBrush(QBrush(sparkle_color))
    painter.drawEllipse(
        QRectF(
            sparkle_center.x() - sparkle_radius,
            sparkle_center.y() - sparkle_radius,
            sparkle_radius * 2,
            sparkle_radius * 2,
        )
    )
    painter.end()
    return pixmap



def _draw_lock_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    stroke = 1.5
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Putar seluruh ikon 45 derajat CCW (kiri)
    # Gembok modern diperbesar: body dan arc lebih dominan
    # Proporsi ideal & tidak terpotong: margin kiri-kanan minimal
    margin = size * 0.05
    body_h = size * 0.48
    body_w_ideal = body_h * 1.42
    body_w_max = size - 2 * margin
    body_w = min(body_w_ideal, body_w_max)
    body_x = (size - body_w) / 2 if body_w < body_w_max else margin
    body_y = size * 0.54 - body_h * 0.18
    rounded = min(size * 0.11, body_h * 0.32)
    painter.drawRoundedRect(
        int(body_x), int(body_y), int(body_w), int(body_h), int(rounded), int(rounded)
    )

    # Shackle: selalu di tengah bodi, proporsional
    shackle_width = body_w * 0.51  # 11/21.5
    shackle_height = body_h * 0.75  # 13.5/18
    shackle_x = body_x + (body_w - shackle_width) / 2 - body_w * 0.07  # geser ke kiri 7% lebar bodi
    shackle_y = body_y - shackle_height * 0.95
    shackle_rect = QRectF(shackle_x, shackle_y, shackle_width, shackle_height)
    shackle_pen = QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
    painter.setPen(shackle_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(shackle_rect, 0, 180 * 16)

    # Tidak ada kaki shackle, agar tidak ada garis vertikal aneh di dalam bodi gembok

    painter.end()
    return pixmap



def _draw_user_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    stroke = max(1.2, size * 0.08)
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    head_size = size * 0.30
    head_x = (size - head_size) / 2
    head_y = size * 0.16
    painter.drawEllipse(
        int(head_x), int(head_y), int(head_size), int(head_size)
    )

    shoulder = QPainterPath()
    shoulder.moveTo(size * 0.18, size * 0.78)
    shoulder.cubicTo(size * 0.22, size * 0.58, size * 0.78, size * 0.58, size * 0.82, size * 0.78)
    painter.drawPath(shoulder)

    painter.end()
    return pixmap



def _draw_check_icon(size: int, color: QColor, charging: bool = False) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    ring_rect = QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64)
    if charging:
        ring_color = QColor("#DDF7FF")
        ring_color.setAlpha(214)
        check_color = QColor("#FFFFFF")
        check_color.setAlpha(246)
    else:
        ring_color = QColor("#F4F8FF")
        ring_color.setAlpha(210)
        check_color = QColor("#FFFFFF")
        check_color.setAlpha(242)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = QPen(ring_color, 1.15)
    pen.setCosmetic(True)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawEllipse(ring_rect)

    check_pen = QPen(check_color, 1.42)
    check_pen.setCosmetic(True)
    check_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    check_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(check_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(size * 0.31, size * 0.52)
    path.lineTo(size * 0.45, size * 0.66)
    path.lineTo(size * 0.72, size * 0.36)
    painter.drawPath(path)

    painter.end()
    return pixmap


def _set_icon(label: QLabel, pixmap: QPixmap) -> None:
    label.setPixmap(pixmap)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)


def _apply_action_button_theme(cancel_btn: CustomButton, submit_btn: CustomButton, charging: bool) -> None:
    cancel_btn.setPrimary(False)
    submit_btn.setPrimary(False)

    def _set_button_shadow(
        button: CustomButton,
        normal_color: QColor,
        normal_blur: int,
        normal_offset_y: int,
        hover_color: QColor,
        hover_blur: int,
        hover_offset_y: int,
    ) -> None:
        button._custom_shadow = (normal_color, normal_blur, normal_offset_y)  # type: ignore[attr-defined]
        button._custom_hover_shadow = (hover_color, hover_blur, hover_offset_y)  # type: ignore[attr-defined]
        button._sync_shadow()  # type: ignore[attr-defined]

    if charging:
        button_gradient = (QColor(22, 47, 64, 238), QColor(18, 65, 88, 242))
        button_hover_gradient = (QColor(28, 61, 82, 246), QColor(24, 91, 122, 248))
        button_border = QColor(103, 224, 255, 138)
        button_border_gradient = (
            QColor(232, 250, 255, 148),
            QColor(103, 224, 255, 126),
            QColor(55, 138, 238, 66),
        )
        button_hover_border_gradient = (
            QColor(245, 253, 255, 178),
            QColor(118, 230, 255, 158),
            QColor(74, 154, 250, 86),
        )
        common_text_color = QColor("#F7FCFF")
        text_shadow_color = QColor(0, 24, 42, 88)

        cancel_btn._custom_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_gradient = button_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_hover_gradient = button_hover_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_border = button_border  # type: ignore[attr-defined]
        cancel_btn._custom_border_gradient = button_border_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_hover_border_gradient = button_hover_border_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]
        cancel_btn._custom_premium_surface = True  # type: ignore[attr-defined]
        cancel_btn._custom_text_shadow_color = text_shadow_color  # type: ignore[attr-defined]

        submit_btn._custom_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_gradient = button_gradient  # type: ignore[attr-defined]
        submit_btn._custom_hover_gradient = button_hover_gradient  # type: ignore[attr-defined]
        submit_btn._custom_border = button_border  # type: ignore[attr-defined]
        submit_btn._custom_border_gradient = button_border_gradient  # type: ignore[attr-defined]
        submit_btn._custom_hover_border_gradient = button_hover_border_gradient  # type: ignore[attr-defined]
        submit_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]
        submit_btn._custom_premium_surface = True  # type: ignore[attr-defined]
        submit_btn._custom_text_shadow_color = text_shadow_color  # type: ignore[attr-defined]

        _set_button_shadow(
            cancel_btn,
            QColor(3, 18, 36, 106),
            17,
            4,
            QColor(26, 167, 228, 86),
            22,
            4,
        )
        _set_button_shadow(
            submit_btn,
            QColor(3, 18, 36, 106),
            17,
            4,
            QColor(26, 167, 228, 86),
            22,
            4,
        )
    else:
        button_gradient = (QColor(42, 51, 64, 236), QColor(27, 36, 49, 242))
        button_hover_gradient = (QColor(54, 64, 79, 246), QColor(36, 47, 62, 248))
        button_border = QColor(255, 255, 255, 104)
        button_border_gradient = (
            QColor(255, 255, 255, 132),
            QColor(255, 255, 255, 92),
            QColor(205, 216, 228, 46),
        )
        button_hover_border_gradient = (
            QColor(255, 255, 255, 164),
            QColor(255, 255, 255, 124),
            QColor(223, 232, 242, 62),
        )
        common_text_color = QColor("#FFFFFF")
        text_shadow_color = QColor(0, 0, 0, 84)

        cancel_btn._custom_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_gradient = button_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_hover_gradient = button_hover_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_border = button_border  # type: ignore[attr-defined]
        cancel_btn._custom_border_gradient = button_border_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_hover_border_gradient = button_hover_border_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]
        cancel_btn._custom_premium_surface = True  # type: ignore[attr-defined]
        cancel_btn._custom_text_shadow_color = text_shadow_color  # type: ignore[attr-defined]

        submit_btn._custom_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_gradient = button_gradient  # type: ignore[attr-defined]
        submit_btn._custom_hover_gradient = button_hover_gradient  # type: ignore[attr-defined]
        submit_btn._custom_border = button_border  # type: ignore[attr-defined]
        submit_btn._custom_border_gradient = button_border_gradient  # type: ignore[attr-defined]
        submit_btn._custom_hover_border_gradient = button_hover_border_gradient  # type: ignore[attr-defined]
        submit_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]
        submit_btn._custom_premium_surface = True  # type: ignore[attr-defined]
        submit_btn._custom_text_shadow_color = text_shadow_color  # type: ignore[attr-defined]

        _set_button_shadow(
            cancel_btn,
            QColor(0, 0, 0, 86),
            16,
            4,
            QColor(255, 255, 255, 58),
            20,
            4,
        )
        _set_button_shadow(
            submit_btn,
            QColor(0, 0, 0, 86),
            16,
            4,
            QColor(255, 255, 255, 58),
            20,
            4,
        )

    cancel_btn.update()
    submit_btn.update()
    cancel_btn._custom_radius = 11.5  # type: ignore[attr-defined]
    submit_btn._custom_radius = 11.5  # type: ignore[attr-defined]


def _draw_credentials_alert_icon(
    size: int,
    accent: QColor,
    mark_color: QColor | None = None,
    fill_alpha: int = 22,
) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    rect = QRectF(2.0, 2.0, size - 4, size - 4)
    painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 120), 1.1))
    painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), fill_alpha))
    painter.drawEllipse(rect)

    if mark_color is None:
        mark_color = QColor(255, 255, 255, 210)
    painter.setPen(QPen(mark_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    body = QRectF(size * 0.31, size * 0.47, size * 0.38, size * 0.28)
    painter.drawRoundedRect(body, size * 0.07, size * 0.07)
    shackle = QRectF(size * 0.36, size * 0.25, size * 0.28, size * 0.30)
    painter.drawArc(shackle, 0, 180 * 16)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(mark_color)
    dot_size = max(2, int(size * 0.075))
    painter.drawEllipse(
        int(size * 0.50 - dot_size / 2),
        int(size * 0.59),
        dot_size,
        dot_size,
    )

    painter.end()
    return pixmap


def _draw_close_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.32
    pen = QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(int(margin), int(margin), int(size - margin), int(size - margin))
    painter.drawLine(int(size - margin), int(margin), int(margin), int(size - margin))

    painter.end()
    return pixmap


class CredentialsWarningDialog(QDialog):
    PALETTES = {
        False: {
            "accent": "#FFFFFF",
            "accent_rgb": "255, 255, 255",
            "border_alpha": "0.34",
            "panel_bg0": "transparent",
            "panel_bg1": "transparent",
            "title_bar_alpha": "0.000",
            "separator_alpha": "0.14",
            "headline_alpha": "0.92",
            "message_alpha": "0.82",
            "close_hover_rgb": "80, 180, 255",
            "close_hover_border_alpha": "0.42",
            "close_hover_bg_alpha": "0.08",
            "close_pressed_bg_alpha": "0.13",
            "close_glow_alpha": 70,
            "icon_fill_alpha": 30,
            "shadow": QColor(255, 255, 255, 56),
        },
        True: {
            "accent": "#50B4FF",
            "accent_rgb": "80, 180, 255",
            "border_alpha": "0.46",
            "panel_bg0": "transparent",
            "panel_bg1": "transparent",
            "title_bar_alpha": "0.000",
            "separator_alpha": "0.18",
            "headline_alpha": "0.94",
            "message_alpha": "0.86",
            "close_hover_rgb": "80, 180, 255",
            "close_hover_border_alpha": "0.58",
            "close_hover_bg_alpha": "0.115",
            "close_pressed_bg_alpha": "0.18",
            "close_glow_alpha": 90,
            "icon_fill_alpha": 34,
            "shadow": QColor(80, 180, 255, 86),
        },
    }
    PIN_PALETTES = {
        False: {
            "accent": "#FFFFFF",
            "accent_rgb": "255, 255, 255",
            "border_alpha": "0.34",
            "panel_bg0": "rgba(30, 36, 46, 0.97)",
            "panel_bg1": "rgba(48, 58, 72, 0.95)",
            "title_bar_alpha": "0.045",
            "separator_alpha": "0.14",
            "headline_alpha": "0.92",
            "message_alpha": "0.82",
            "close_hover_rgb": "80, 180, 255",
            "close_hover_border_alpha": "0.42",
            "close_hover_bg_alpha": "0.08",
            "close_pressed_bg_alpha": "0.13",
            "close_glow_alpha": 70,
            "icon_fill_alpha": 30,
            "shadow": QColor(255, 255, 255, 56),
        },
        True: {
            "accent": "#50B4FF",
            "accent_rgb": "80, 180, 255",
            "border_alpha": "0.46",
            "panel_bg0": "rgba(24, 40, 66, 0.98)",
            "panel_bg1": "rgba(36, 70, 106, 0.96)",
            "title_bar_alpha": "0.045",
            "separator_alpha": "0.18",
            "headline_alpha": "0.94",
            "message_alpha": "0.86",
            "close_hover_rgb": "80, 180, 255",
            "close_hover_border_alpha": "0.58",
            "close_hover_bg_alpha": "0.115",
            "close_pressed_bg_alpha": "0.18",
            "close_glow_alpha": 90,
            "icon_fill_alpha": 34,
            "shadow": QColor(80, 180, 255, 86),
        },
    }
    WIDTH_MIN = 300
    HEIGHT = 152
    RADIUS = 18
    TITLE_BAR_HEIGHT = 36
    TITLE_MAX_RESERVED_WIDTH = 74
    TEXT_MAX_RESERVED_WIDTH = 88
    TEXT_MAX_MIN_WIDTH = 180
    TITLE_MAX_MIN_WIDTH = 120
    CLOSE_ICON_SIZE = 14
    CLOSE_ICON_HOVER_SIZE = 15
    CLOSE_ICON_PRESSED_SIZE = 13
    CLOSE_BUTTON_SIZE = 20
    CREDENTIAL_ICON_SIZE = 26
    SEPARATOR_HEIGHT = 1

    def __init__(
        self,
        parent: QWidget,
        title: str,
        message: str,
        charging: bool,
        width: int,
        window_title: str = "Secure Access",
        visual_mode: str = "credentials",
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._message = message
        self._window_title = window_title
        self._visual_mode = visual_mode
        self._charging = charging
        self._palette = self._resolve_palette(charging)
        self._warning_width = max(self.WIDTH_MIN, width)
        self._accent = QColor(self._palette["accent"])
        self._accent_rgb = self._palette["accent_rgb"]
        self._drag_offset: QPoint | None = None
        self._close_btn: QToolButton | None = None
        self._icon_label: QLabel | None = None
        self._panel: QFrame | None = None
        self._charging_timer: QTimer | None = None
        self._close_icon_anim: QPropertyAnimation | None = None

        self._configure_window()
        self._apply_theme()
        self._build_layout()
        self._center_on_parent()
        self._start_charging_timer()

    def _resolve_palette(self, charging: bool) -> dict[str, object]:
        if self._visual_mode == "pin":
            return self.PIN_PALETTES[charging]
        return self.PALETTES[charging]

    def _uses_lock_reference_warning(self) -> bool:
        return self._visual_mode in {"credentials", "pin"}

    def _set_charging(self, charging: bool) -> None:
        if self._charging == charging:
            return
        self._charging = charging
        self._palette = self._resolve_palette(charging)
        self._accent = QColor(self._palette["accent"])
        self._accent_rgb = self._palette["accent_rgb"]
        if isinstance(self._panel, LockReferenceWarningPanel):
            self._panel.set_charging(charging)
        self._apply_theme()
        if self._icon_label is not None:
            self._icon_label.setPixmap(self._draw_warning_icon())
        self._apply_panel_shadow()
        self._set_close_hover(False)
        self._refresh_theme_tree()

    def _pin_accent_color(self) -> QColor:
        color = QColor(self._accent)
        color.setAlphaF(float(self._palette.get("headline_alpha", "0.92")))
        return color

    def _draw_warning_icon(self) -> QPixmap:
        if self._uses_lock_reference_warning():
            return _draw_credentials_alert_icon(
                self.CREDENTIAL_ICON_SIZE,
                self._accent,
                self._pin_accent_color(),
                int(self._palette.get("icon_fill_alpha", 34)),
            )
        return _draw_credentials_alert_icon(self.CREDENTIAL_ICON_SIZE, self._accent)

    def _read_current_charging(self) -> bool:
        parent = self.parentWidget()
        provider = getattr(parent, "_pin_charging_provider", None)
        if self._visual_mode == "pin" and callable(provider):
            try:
                return bool(provider())
            except Exception:
                pass

        try:
            from ui.battery_status import get_battery_info
        except ImportError:
            from src.ui.battery_status import get_battery_info  # type: ignore

        info = get_battery_info()
        if not info:
            return self._charging
        charging = info.get("charging")
        if isinstance(charging, bool):
            return charging
        if isinstance(charging, int):
            return bool(charging)
        return self._charging

    def _start_charging_timer(self) -> None:
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(lambda: self._set_charging(self._read_current_charging()))
        self._charging_timer.start(500)

    def _configure_window(self) -> None:
        self.setObjectName("credentialsWarningDialog")
        self.setWindowTitle(self._title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self._warning_width, self.HEIGHT)

    def _apply_theme(self) -> None:
        if self._uses_lock_reference_warning():
            panel_style = "border: none; background: transparent;"
            title_bar_style = "border: none; background: transparent;"
        else:
            panel_style = f"""
                border: 1px solid rgba({self._accent_rgb}, {self._palette["border_alpha"]});
                border-radius: {self.RADIUS}px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self._palette["panel_bg0"]},
                    stop:1 {self._palette["panel_bg1"]}
                );
            """
            title_bar_style = f"border: none; background: rgba(255, 255, 255, {self._palette.get('title_bar_alpha', '0.025')});"
        title_rgb = self._accent_rgb if self._uses_lock_reference_warning() else "244, 248, 255"
        title_alpha = (
            self._palette.get("headline_alpha", "0.92")
            if self._uses_lock_reference_warning()
            else "0.74"
        )
        close_hover_rgb = self._palette.get("close_hover_rgb", self._accent_rgb)
        close_hover_border_rgb = close_hover_rgb if self._uses_lock_reference_warning() else "255, 255, 255"
        close_hover_border_alpha = self._palette.get("close_hover_border_alpha", "0.58" if self._uses_lock_reference_warning() else "0.18")
        close_hover_bg_rgb = close_hover_rgb if self._uses_lock_reference_warning() else "255, 255, 255"
        close_hover_bg_alpha = self._palette.get("close_hover_bg_alpha", "0.115" if self._uses_lock_reference_warning() else "0.052")
        close_pressed_bg_rgb = close_hover_rgb if self._uses_lock_reference_warning() else "255, 255, 255"
        close_pressed_bg_alpha = self._palette.get("close_pressed_bg_alpha", "0.18" if self._uses_lock_reference_warning() else "0.085")
        message_rgb = self._accent_rgb if self._uses_lock_reference_warning() else "244, 248, 255"
        message_alpha = (
            self._palette.get("message_alpha", "0.86")
            if self._uses_lock_reference_warning()
            else self._palette.get("message_alpha", "0.80")
        )
        self.setStyleSheet(f"""
            QDialog#credentialsWarningDialog {{
                background: transparent;
            }}
            QFrame#warningPanel {{
                {panel_style}
            }}
            QFrame#warningTitleBar {{
                {title_bar_style}
            }}
            QFrame#warningSeparator {{
                border: none;
                background: rgba({self._accent_rgb}, {self._palette.get("separator_alpha", "0.10")});
            }}
            QLabel#warningIcon {{
                min-width: 30px;
                max-width: 30px;
            }}
            QLabel#warningWindowTitle {{
                color: rgba({title_rgb}, {title_alpha});
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.2px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QToolButton#warningClose {{
                border: 1px solid rgba(255, 255, 255, 0.00);
                border-radius: 8px;
                background: transparent;
            }}
            QToolButton#warningClose:hover {{
                border: 1px solid rgba({close_hover_border_rgb}, {close_hover_border_alpha});
                background: rgba({close_hover_bg_rgb}, {close_hover_bg_alpha});
            }}
            QToolButton#warningClose:pressed {{
                background: rgba({close_pressed_bg_rgb}, {close_pressed_bg_alpha});
            }}
            QLabel#warningHeadline {{
                color: rgba({self._accent_rgb}, {self._palette.get("headline_alpha", "0.92")});
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.2px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QLabel#warningMessage {{
                color: rgba({message_rgb}, {message_alpha});
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
        """)

    def _apply_panel_shadow(self) -> None:
        if self._panel is None:
            return
        # Keep the warning dialog inside its translucent window bounds.
        # External QGraphicsDropShadowEffect can produce negative dirty rects on
        # Windows layered windows when the charger state repaints the dialog.
        self._panel.setGraphicsEffect(None)  # type: ignore[arg-type]

    def _refresh_theme_tree(self) -> None:
        for widget in [self, *self.findChildren(QWidget)]:
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._uses_lock_reference_warning():
            self._panel = LockReferenceWarningPanel(self._charging, self)
        else:
            self._panel = QFrame(self)
        self._panel.setObjectName("warningPanel")
        panel_layout = QVBoxLayout(self._panel)
        if self._uses_lock_reference_warning():
            panel_layout.setContentsMargins(1, 1, 1, 1)
        else:
            panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        panel_layout.addWidget(self._build_title_bar(self._panel))
        panel_layout.addLayout(self._build_separator(self._panel))
        panel_layout.addLayout(self._build_content(self._panel))
        layout.addWidget(self._panel)
        self._apply_panel_shadow()

        if self._close_btn is not None:
            self._close_btn.setFocus()

    def _build_title_bar(self, panel: QFrame) -> QFrame:
        title_bar_frame = QFrame(panel)
        title_bar_frame.setObjectName("warningTitleBar")
        title_bar_frame.setFixedHeight(self.TITLE_BAR_HEIGHT)
        title_bar_frame.setCursor(Qt.CursorShape.ArrowCursor)
        title_bar = QHBoxLayout(title_bar_frame)
        title_bar.setContentsMargins(16, 0, 10, 0)
        title_bar.setSpacing(10)

        window_title = QLabel(self._window_title, title_bar_frame)
        window_title.setObjectName("warningWindowTitle")
        window_title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        window_title.setMaximumWidth(max(self.TITLE_MAX_MIN_WIDTH, self._warning_width - self.TITLE_MAX_RESERVED_WIDTH))
        title_bar.addWidget(window_title)
        title_bar.addStretch(1)

        self._close_btn = QToolButton(title_bar_frame)
        self._close_btn.setObjectName("warningClose")
        close_icon_color = QColor(self._accent) if self._uses_lock_reference_warning() else QColor(244, 248, 255, 185)
        if self._uses_lock_reference_warning():
            close_icon_color.setAlphaF(float(self._palette.get("headline_alpha", "0.92")))
        self._close_btn.setIcon(QIcon(_draw_close_icon(self.CLOSE_ICON_SIZE, close_icon_color)))
        self._close_btn.setIconSize(QSize(self.CLOSE_ICON_SIZE, self.CLOSE_ICON_SIZE))
        self._close_btn.setFixedSize(self.CLOSE_BUTTON_SIZE, self.CLOSE_BUTTON_SIZE)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setToolTip("Close")
        self._close_btn.setAccessibleName("Close")
        self._close_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._close_btn.clicked.connect(self.reject)
        self._close_btn.enterEvent = self._close_enter  # type: ignore[method-assign]
        self._close_btn.leaveEvent = self._close_leave  # type: ignore[method-assign]
        self._close_btn.mousePressEvent = self._close_mouse_press  # type: ignore[method-assign]
        self._close_btn.mouseReleaseEvent = self._close_mouse_release  # type: ignore[method-assign]
        title_bar.addWidget(self._close_btn)

        title_bar_frame.mousePressEvent = self._start_drag  # type: ignore[method-assign]
        title_bar_frame.mouseMoveEvent = self._move_drag  # type: ignore[method-assign]
        title_bar_frame.mouseReleaseEvent = self._stop_drag  # type: ignore[method-assign]
        return title_bar_frame

    def _build_separator(self, panel: QFrame) -> QHBoxLayout:
        separator = QFrame(panel)
        separator.setObjectName("warningSeparator")
        separator.setFixedHeight(self.SEPARATOR_HEIGHT)
        separator_row = QHBoxLayout()
        separator_row.setContentsMargins(16, 0, 16, 0)
        separator_row.addWidget(separator)
        return separator_row

    def _build_content(self, panel: QFrame) -> QHBoxLayout:
        content_row = QHBoxLayout()
        content_row.setContentsMargins(18, 18, 18, 20)
        content_row.setSpacing(11)

        self._icon_label = QLabel(panel)
        self._icon_label.setObjectName("warningIcon")
        self._icon_label.setPixmap(self._draw_warning_icon())
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_row.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(7)

        headline_label = QLabel(self._title, panel)
        headline_label.setObjectName("warningHeadline")
        headline_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        headline_label.setMaximumWidth(max(self.TEXT_MAX_MIN_WIDTH, self._warning_width - self.TEXT_MAX_RESERVED_WIDTH))
        text_column.addWidget(headline_label)

        message_label = QLabel(self._message, panel)
        message_label.setObjectName("warningMessage")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        message_label.setMaximumWidth(max(self.TEXT_MAX_MIN_WIDTH, self._warning_width - self.TEXT_MAX_RESERVED_WIDTH))
        text_column.addWidget(message_label)
        content_row.addLayout(text_column, 1)
        content_row.setAlignment(text_column, Qt.AlignmentFlag.AlignVCenter)
        return content_row

    def _center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        parent_top_left = parent.mapToGlobal(parent.rect().topLeft())
        self.move(
            parent_top_left.x() + (parent.width() - self.width()) // 2,
            parent_top_left.y() + (parent.height() - self.height()) // 2,
        )

    def _set_close_hover(self, hovered: bool) -> None:
        if self._close_btn is None:
            return
        if self._uses_lock_reference_warning():
            if hovered and not self._charging:
                close_icon_color = QColor(80, 180, 255, 255)
            elif hovered:
                close_icon_color = QColor(255, 255, 255, 245)
            else:
                close_icon_color = QColor(self._accent)
            if not hovered:
                close_icon_color.setAlphaF(float(self._palette.get("headline_alpha", "0.92")))
            if hovered:
                close_icon_color.setAlpha(255)
                glow_rgb = [int(channel.strip()) for channel in str(self._palette.get("close_hover_rgb", self._accent_rgb)).split(",")]
                shadow = QGraphicsDropShadowEffect(self._close_btn)
                shadow.setBlurRadius(12)
                shadow.setOffset(0, 0)
                shadow.setColor(QColor(
                    glow_rgb[0],
                    glow_rgb[1],
                    glow_rgb[2],
                    int(self._palette.get("close_glow_alpha", 90)),
                ))
                self._close_btn.setGraphicsEffect(shadow)
            else:
                self._close_btn.setGraphicsEffect(None)  # type: ignore[arg-type]
        else:
            close_icon_color = QColor(self._accent) if hovered else QColor(244, 248, 255, 185)
            if hovered:
                close_icon_color.setAlpha(225)
            self._close_btn.setGraphicsEffect(None)  # type: ignore[arg-type]
        self._close_btn.setIcon(QIcon(_draw_close_icon(self.CLOSE_ICON_SIZE, close_icon_color)))
        self._close_btn.style().polish(self._close_btn)

    def _animate_close_icon_size(self, target_size: int) -> None:
        if self._close_btn is None:
            return
        if self._close_icon_anim is not None:
            self._close_icon_anim.stop()
        anim = QPropertyAnimation(self._close_btn, b"iconSize", self)
        anim.setDuration(120)
        anim.setStartValue(self._close_btn.iconSize())
        anim.setEndValue(QSize(target_size, target_size))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: setattr(self, "_close_icon_anim", None))
        self._close_icon_anim = anim
        anim.start()

    def _close_enter(self, event) -> None:
        self._set_close_hover(True)
        self._animate_close_icon_size(self.CLOSE_ICON_HOVER_SIZE)
        event.accept()

    def _close_leave(self, event) -> None:
        self._set_close_hover(False)
        self._animate_close_icon_size(self.CLOSE_ICON_SIZE)
        event.accept()

    def _close_mouse_press(self, event) -> None:
        if self._close_btn is not None and event.button() == Qt.MouseButton.LeftButton:
            self._animate_close_icon_size(self.CLOSE_ICON_PRESSED_SIZE)
        QToolButton.mousePressEvent(self._close_btn, event)

    def _close_mouse_release(self, event) -> None:
        if self._close_btn is not None and event.button() == Qt.MouseButton.LeftButton:
            target_size = self.CLOSE_ICON_HOVER_SIZE if self._close_btn.underMouse() else self.CLOSE_ICON_SIZE
            self._animate_close_icon_size(target_size)
        QToolButton.mouseReleaseEvent(self._close_btn, event)

    def _start_drag(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _move_drag(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def _stop_drag(self, event) -> None:
        self._drag_offset = None
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        if self._charging_timer is not None:
            self._charging_timer.stop()
        super().closeEvent(event)


def _show_credentials_warning(
    parent: QWidget,
    title: str,
    message: str,
    charging: bool,
    width: int,
    window_title: str = "Secure Access",
    visual_mode: str = "credentials",
) -> None:
    CredentialsWarningDialog(parent, title, message, charging, width, window_title, visual_mode).exec()


def _resolve_credentials_enter_action(username: str, password: str, focused_field: str) -> tuple[str, str, str]:
    username = username.strip()
    if focused_field in {"username", "form"} and username and not password:
        return ("focus_password", "", "")
    if not username and not password:
        return ("focus_username", "Credentials Required", "Enter username and password to continue.")
    if not username:
        return ("focus_username", "Username Required", "Enter username to continue.")
    if not password:
        return ("focus_password", "Password Required", "Enter password to continue.")
    return ("submit", "", "")


def show_credentials_login(app: QApplication, pin_user: User, parent: Optional[QWidget] = None) -> Optional[User]:
    """Step 2: username/password validation after successful PIN step."""
    dialog = PremiumCredentialsDialog(parent)
    dialog.setObjectName("credentialsDialog")
    dialog.setWindowTitle("Verifikasi Username & Password")
    dialog.setModal(True)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)

    width_px = 405
    height_px = int(18.5 * 0.3937 * 96)
    dialog.setFixedSize(width_px, height_px)

    screen_geometry = app.primaryScreen().geometry()
    x = screen_geometry.x() + (screen_geometry.width() - width_px) // 2
    y = screen_geometry.y() + (screen_geometry.height() - height_px) // 2
    dialog.move(x, y)

    _BASE_SHEET = """
        QDialog#credentialsDialog {{
            background: transparent;
            border: none;
        }}
        QLabel {{
            color: #f4f8ff;
            font-family: {font_stack};
            font-size: 13px;
        }}
        QFrame#cardPanel {{
            border: none;
            background: transparent;
        }}
        QFrame#topGlow {{
            border: none;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,0,0,0),
                stop:0.5 {glow},
                stop:1 rgba(0,0,0,0)
            );
        }}
        QLabel#fieldLabel {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
            color: {label_color};
            font-family: {font_stack};
        }}
        QFrame#inputRow {{
            border: none;
            background: transparent;
        }}
        QFrame#inputRow[focused="true"] {{
            border: none;
            background: transparent;
        }}
        QFrame#statusChip {{
            border: none;
            background: transparent;
        }}
        QLabel#fieldIcon {{
            min-width: 24px;
            max-width: 24px;
        }}
        QLineEdit#fieldInput {{
            color: #edf4ff;
            border: none;
            background: transparent;
            padding: 0px 4px;
            font-size: 14px;
            font-family: {font_stack};
        }}
        QLineEdit#fieldInput[identityLocked="true"] {{
            color: {locked_identity_color};
            font-weight: 650;
        }}
        QLineEdit#fieldInput::placeholder {{
            color: {placeholder_color};
        }}
        QToolButton#togglePassword {{
            border: none;
            background: transparent;
            padding: 2px 6px;
        }}
        QLabel#statusIcon {{
            min-width: 22px;
            max-width: 22px;
        }}
        QLabel#statusText {{
            color: {status_color};
            font-size: 12px;
            font-family: {font_stack};
        }}
    """

    # Samakan background utama dengan login.py (charging & tidak charging)
    _STYLE_NORMAL = _BASE_SHEET.format(
        font_stack=CREDENTIALS_FONT_STACK,
        card_border="transparent",
        card_bg0="transparent",
        card_bg_mid="transparent",
        card_bg1="transparent",
        glow="rgba(255, 255, 255, 0.36)",
        label_color="#FFFFFF",
        input_border="rgba(255, 255, 255, 0.18)",
        input_focus_border="rgba(255, 255, 255, 0.38)",
        input_row_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(35, 43, 55, 0.70), "
            "stop:1 rgba(21, 29, 40, 0.62)"
            ")"
        ),
        input_focus_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(45, 55, 69, 0.84), "
            "stop:1 rgba(28, 37, 50, 0.76)"
            ")"
        ),
        locked_identity_color="rgba(246, 250, 255, 0.94)",
        placeholder_color="rgba(230, 237, 246, 0.42)",
        status_color="#FFFFFF",
        status_border="rgba(255, 255, 255, 0.16)",
        status_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(255, 255, 255, 0.070), "
            "stop:1 rgba(255, 255, 255, 0.030)"
            ")"
        ),
        cancel_border="#D3D3D3",
        cancel_color="#333333",
        submit_border="#D3D3D3",
        submit0="#C0C0C0", submit1="#E8E8E8",
        submit_h0="#E8E8E8", submit_h1="#FFFFFF",
    )

    _STYLE_CHARGING = _BASE_SHEET.format(
        font_stack=CREDENTIALS_FONT_STACK,
        card_border="transparent",
        card_bg0="transparent",
        card_bg_mid="transparent",
        card_bg1="transparent",
        glow="rgba(103, 224, 255, 0.46)",
        label_color="#F7FCFF",
        input_border="rgba(236, 251, 255, 0.19)",
        input_focus_border="rgba(103, 224, 255, 0.46)",
        input_row_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(35, 49, 64, 0.76), "
            "stop:1 rgba(22, 35, 51, 0.68)"
            ")"
        ),
        input_focus_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(39, 61, 80, 0.86), "
            "stop:1 rgba(22, 48, 70, 0.80)"
            ")"
        ),
        locked_identity_color="rgba(221, 247, 255, 0.96)",
        placeholder_color="rgba(224, 240, 250, 0.46)",
        status_color="#FFFFFF",
        status_border="rgba(236, 251, 255, 0.18)",
        status_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(236, 251, 255, 0.078), "
            "stop:1 rgba(103, 224, 255, 0.040)"
            ")"
        ),
        cancel_border="rgba(80, 180, 255, 0.40)",
        cancel_color="#50B4FF",
        submit_border="rgba(80, 180, 255, 0.45)",
        submit0="#0d72cc", submit1="#50B4FF",
        submit_h0="#1580dc", submit_h1="#7dd8ff",
    )

    _TITLE_NORMAL = (
        "<p style='margin:0; padding:0; font-size:20px; font-weight:620; letter-spacing:0px; color:#FFFFFF;'>"
        "Secure Access</p>"
        "<p style='margin:5px 0 0 0; padding:0; font-size:12px; color:rgba(230,237,246,0.72); font-weight:400;'>"
        "Verify your credentials to continue</p>"
    )
    _TITLE_CHARGING = (
        "<p style='margin:0; padding:0; font-size:20px; font-weight:620; letter-spacing:0px; color:#FFFFFF;'>"
        "Secure Access</p>"
        "<p style='margin:5px 0 0 0; padding:0; font-size:12px; color:rgba(213,244,255,0.76); font-weight:400;'>"
        "Verify your credentials to continue</p>"
    )

    dialog.setStyleSheet(_STYLE_NORMAL)

    root_layout = QVBoxLayout(dialog)
    root_layout.setContentsMargins(36, 0, 36, 0)
    root_layout.setSpacing(0)

    root_layout.addStretch(1)

    title = QLabel(_TITLE_NORMAL)
    title.setObjectName("title")
    title.setTextFormat(Qt.TextFormat.RichText)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_glow = QGraphicsDropShadowEffect(title)
    title_glow.setBlurRadius(11)
    title_glow.setOffset(0, 0)
    title_glow.setColor(QColor(255, 255, 255, 42))
    title.setGraphicsEffect(title_glow)
    root_layout.addWidget(title)
    root_layout.addSpacing(18)

    card = LockReferenceCardPanel(False)
    card.setObjectName("cardPanel")
    # Shadow utama menggunakan warna border card panel yang lebih kuat
    card_shadow = QGraphicsDropShadowEffect(card)
    card_shadow.setBlurRadius(18)
    card_shadow.setOffset(0, 8)
    card_shadow.setColor(QColor(0, 0, 0, 85))
    card.setGraphicsEffect(card_shadow)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(24, 18, 24, 22)
    card_layout.setSpacing(10)

    # from PySide6.QtCore import QPropertyAnimation, Property  # Unused, remove
    from PySide6.QtGui import QPainter, QLinearGradient, QBrush


    class ShimmerGlow(QFrame):
        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self.setObjectName("topGlow")
            self.setFixedHeight(2)
            self._charging = False
            self._color_charging = QColor(80, 180, 255, 180)
            self._color_charging_core = QColor(80, 180, 255, 255)
            self._color_normal = QColor(255, 255, 255, 76)
            self._color_normal_core = QColor(255, 255, 255, 136)
            self._shimmer_active = True
            self._shimmer_pos = 0.0
            from PySide6.QtCore import QEasingCurve, QSequentialAnimationGroup, QPauseAnimation, QPropertyAnimation

            self._anim_group = QSequentialAnimationGroup(self)
            shimmer_anim = QPropertyAnimation(self, b"shimmerPos")
            shimmer_anim.setStartValue(0.0)
            shimmer_anim.setEndValue(1.0)
            shimmer_anim.setDuration(2000)  # 2 detik per siklus
            shimmer_anim.setEasingCurve(QEasingCurve.Type.Linear)
            pause = QPauseAnimation(600)  # jeda 0.6 detik
            self._anim_group.addAnimation(shimmer_anim)
            self._anim_group.addAnimation(pause)
            self._anim_group.setLoopCount(2)  # hanya 2 kali
            self._anim_group.finished.connect(self._on_shimmer_finished)

        def start_shimmer(self):
            self._shimmer_active = True
            self._shimmer_pos = 0.0
            self.show()
            self._anim_group.stop()
            self._anim_group.setLoopCount(2)
            self._anim_group.start()

        def _on_shimmer_finished(self):
            self._shimmer_active = False
            self._shimmer_pos = 0.0
            self.update()

        def setCharging(self, charging: bool):
            self._charging = charging
            self.update()


        def getShimmerPos(self) -> float:
            return float(self._shimmer_pos)

        def setShimmerPos(self, value: float) -> None:
            self._shimmer_pos = float(value)
            self.update()

        from PySide6.QtCore import Property
        shimmerPos = Property(float, getShimmerPos, setShimmerPos)

        from PySide6.QtGui import QPaintEvent
        def paintEvent(self, event: QPaintEvent) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w = self.width()
            h = self.height()
            base = self._color_charging if self._charging else self._color_normal
            core = self._color_charging_core if self._charging else self._color_normal_core
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor(0,0,0,0))
            grad.setColorAt(0.2, base)
            grad.setColorAt(0.5, core)
            grad.setColorAt(0.8, base)
            grad.setColorAt(1.0, QColor(0,0,0,0))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            if self._shimmer_active:
                # shimmer effect: overlay moving white highlight
                from PySide6.QtGui import QLinearGradient as QLG
                highlight = QLG(0, 0, w, 0)
                pos = self._shimmer_pos
                highlight.setColorAt(max(0.0, pos-0.08), QColor(255,255,255,0))
                highlight.setColorAt(pos, QColor(255,255,255,120))
                highlight.setColorAt(min(1.0, pos+0.08), QColor(255,255,255,0))
                painter.fillRect(0, 0, w, h, grad)
                painter.fillRect(0, 0, w, h, highlight)
            else:
                painter.drawRect(0, 0, w, h)

    top_glow = ShimmerGlow()
    card_layout.addWidget(top_glow)
    # Jalankan shimmer hanya 2 kali saat form dibuat
    top_glow.start_shimmer()

    username_label = QLabel("Username")
    username_label.setObjectName("fieldLabel")
    # Efek glow awal
    username_glow = QGraphicsDropShadowEffect(username_label)
    username_glow.setBlurRadius(5)
    username_glow.setOffset(0, 0)
    username_glow.setColor(QColor(255, 255, 255, 24))
    username_label.setGraphicsEffect(username_glow)
    card_layout.addWidget(username_label)
    card_layout.addSpacing(8)  # Tambahkan jarak 8px antara label dan textbox user

    username_row = CredentialsGlassInputRow()
    username_row.setObjectName("inputRow")
    username_row.setProperty("focused", False)
    username_row.setFixedHeight(41)
    username_row_shadow = QGraphicsDropShadowEffect(username_row)
    username_row_shadow.setBlurRadius(11)
    username_row_shadow.setOffset(0, 3)
    username_row_shadow.setColor(QColor(0, 0, 0, 58))
    username_row.setGraphicsEffect(username_row_shadow)
    username_layout = QHBoxLayout(username_row)
    username_layout.setContentsMargins(14, 0, 14, 0)
    username_layout.setSpacing(10)

    username_icon = QLabel()
    username_icon.setObjectName("fieldIcon")
    _set_icon(username_icon, _draw_user_icon(18, QColor("#F4F8FF")))

    username_input = QLineEdit()
    username_input.setObjectName("fieldInput")
    username_input.setPlaceholderText("Enter username")
    username_input.setText(str(getattr(pin_user, "username", "") or ""))
    username_input.setReadOnly(True)
    username_input.setProperty("identityLocked", True)
    username_input.setCursor(Qt.CursorShape.ArrowCursor)
    username_input.setToolTip("Verified PIN identity")
    username_input.setAccessibleName("Verified username")
    username_input.installEventFilter(CredentialsInputFocusFilter(username_row))

    username_layout.addWidget(username_icon)
    username_layout.addWidget(username_input)
    card_layout.addWidget(username_row)
    # Tambahkan jarak antara input username dan input password
    card_layout.addSpacing(14)

    password_label = QLabel("Password")
    password_label.setObjectName("fieldLabel")
    # Efek glow awal
    password_glow = QGraphicsDropShadowEffect(password_label)
    password_glow.setBlurRadius(5)
    password_glow.setOffset(0, 0)
    password_glow.setColor(QColor(255, 255, 255, 24))
    password_label.setGraphicsEffect(password_glow)
    card_layout.addWidget(password_label)
    card_layout.addSpacing(8)  # Tambahkan jarak 8px antara label dan textbox password

    password_row = CredentialsGlassInputRow()
    password_row.setObjectName("inputRow")
    password_row.setProperty("focused", False)
    password_row.setFixedHeight(41)
    password_row_shadow = QGraphicsDropShadowEffect(password_row)
    password_row_shadow.setBlurRadius(11)
    password_row_shadow.setOffset(0, 3)
    password_row_shadow.setColor(QColor(0, 0, 0, 58))
    password_row.setGraphicsEffect(password_row_shadow)
    password_layout = QHBoxLayout(password_row)
    password_layout.setContentsMargins(14, 0, 14, 0)
    password_layout.setSpacing(10)

    password_icon = QLabel()
    password_icon.setObjectName("fieldIcon")
    _set_icon(password_icon, _draw_lock_icon(18, QColor("#F4F8FF")))

    password_input = QLineEdit()
    password_input.setObjectName("fieldInput")
    password_input.setEchoMode(QLineEdit.EchoMode.Password)
    password_input.setPlaceholderText("Enter password")
    password_input.installEventFilter(CredentialsInputFocusFilter(password_row))

    toggle_password_btn = QToolButton()
    toggle_password_btn.setObjectName("togglePassword")
    toggle_password_btn.setIconSize(QSize(18, 18))
    # Set initial outline color (non-charging)
    # Outline color non-charging disamakan dengan aksen card panel
    # Set ikon awal: crossed=True karena mode Password (karakter disembunyikan)
    # Set ikon awal stroke-only agar konsisten dengan ikon field.
    toggle_password_btn.setIcon(QIcon(_draw_eye_icon(18, QColor("#F4F8FF"), crossed=True)))
    toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    toggle_password_btn.installEventFilter(CredentialsInputFocusFilter(password_row))

    password_layout.addWidget(password_icon)
    password_layout.addWidget(password_input)
    password_layout.addWidget(toggle_password_btn)
    card_layout.addWidget(password_row)
    # Tambahkan jarak antara input password dan status row
    card_layout.addSpacing(22)

    status_chip = CredentialsGlassStatusChip()
    status_chip.setObjectName("statusChip")
    status_chip.setFixedHeight(34)
    status_chip_shadow = QGraphicsDropShadowEffect(status_chip)
    status_chip_shadow.setBlurRadius(12)
    status_chip_shadow.setOffset(0, 3)
    status_chip_shadow.setColor(QColor(0, 0, 0, 54))
    status_chip.setGraphicsEffect(status_chip_shadow)
    status_row = QHBoxLayout(status_chip)
    status_row.setContentsMargins(12, 0, 12, 0)
    status_row.setSpacing(8)
    status_icon = QLabel()
    status_icon.setObjectName("statusIcon")
    _set_icon(status_icon, _draw_check_icon(18, QColor("#FFFFFF"), False))
    # Tambahkan efek glow putih pada status_icon agar konsisten dengan status_text
    status_icon_glow = QGraphicsDropShadowEffect(status_icon)
    status_icon_glow.setBlurRadius(5)
    status_icon_glow.setOffset(0, 0)
    status_icon_glow.setColor(QColor(255, 255, 255, 28))
    status_icon.setGraphicsEffect(status_icon_glow)
    status_text = QLabel(f"PIN verified · <span style='font-size:12px; font-weight:650;'>{getattr(pin_user, 'username', '-')}</span>")
    status_text.setObjectName("statusText")
    status_text.setTextFormat(Qt.TextFormat.RichText)
    # Efek glow awal
    status_glow = QGraphicsDropShadowEffect(status_text)
    status_glow.setBlurRadius(5)
    status_glow.setOffset(0, 0)
    status_glow.setColor(QColor(255, 255, 255, 30))
    status_text.setGraphicsEffect(status_glow)
    status_row.addWidget(status_icon)
    status_row.addWidget(status_text)
    status_row.addStretch(1)
    card_layout.addWidget(status_chip)

    root_layout.addWidget(card)
    root_layout.addSpacing(14)

    result_user: dict[str, Optional[User]] = {"user": None}

    buttons = QHBoxLayout()
    buttons.setSpacing(12)

    cancel_btn = CustomButton("Cancel", primary=False)
    cancel_btn.setObjectName("cancelButtonFixed")
    cancel_btn.setMinimumSize(100, 41)
    cancel_btn.setMaximumSize(100, 41)
    cancel_btn.setStyleSheet("")  # type: ignore  # Kosongkan stylesheet agar tidak override
    submit_btn = CustomButton("Sign In", primary=True)
    submit_btn.setObjectName("submitButtonFixed")
    submit_btn.setMinimumSize(100, 41)
    submit_btn.setMaximumSize(100, 41)
    submit_btn.setStyleSheet("")  # type: ignore
    from PySide6.QtWidgets import QGraphicsEffect
    from typing import cast
    for btn in [cancel_btn, submit_btn]:
        btn.setGraphicsEffect(cast(QGraphicsEffect, None))
    _apply_action_button_theme(cancel_btn, submit_btn, charging=False)
    buttons.addWidget(cancel_btn, 0)
    buttons.addWidget(submit_btn, 0)
    root_layout.addLayout(buttons)
    root_layout.addStretch(1)

    def toggle_password_visibility() -> None:
        is_hidden = password_input.echoMode() == QLineEdit.EchoMode.Password
        password_input.setEchoMode(QLineEdit.EchoMode.Normal if is_hidden else QLineEdit.EchoMode.Password)
        # Ikuti warna outline dari status charging
        charging = bool(_charging_cache.get("prev"))
        crossed = password_input.echoMode() == QLineEdit.EchoMode.Password
        eye_color = QColor("#DDF7FF") if charging else QColor("#F4F8FF")
        toggle_password_btn.setIcon(QIcon(_draw_eye_icon(18, eye_color, crossed=crossed)))

    def on_submit() -> None:
        username = username_input.text().strip()
        password = password_input.text()
        if not username or not password:
            action, title_text, message_text = _resolve_credentials_enter_action(username, password, "form")
            if action == "focus_username":
                username_input.setFocus()
            elif action == "focus_password":
                password_input.setFocus()
            if title_text and message_text:
                _show_credentials_warning(
                    dialog,
                    title_text,
                    message_text,
                    bool(_charging_cache.get("prev")),
                    card.width(),
                )
            return

        authenticated_user = authenticate_credentials_step(
            pin_user=pin_user,
            username=username,
            password=password,
            ip_address="local-app",
            user_agent="PySide6",
        )
        if authenticated_user is None:
            _show_credentials_warning(
                dialog,
                "Sign In Failed",
                "Check your username and password.",
                bool(_charging_cache.get("prev")),
                card.width(),
            )
            return

        result_user["user"] = authenticated_user
        dialog.accept()

    toggle_password_btn.clicked.connect(toggle_password_visibility)
    submit_btn.clicked.connect(on_submit)
    cancel_btn.clicked.connect(dialog.reject)

    def _handle_enter_key() -> None:
        focused_widget = app.focusWidget()
        focused_field = "username" if focused_widget is username_input else "password" if focused_widget is password_input else "form"
        action, title_text, message_text = _resolve_credentials_enter_action(
            username_input.text(),
            password_input.text(),
            focused_field,
        )
        if action == "focus_username":
            username_input.setFocus()
        elif action == "focus_password":
            password_input.setFocus()
        elif action == "submit":
            on_submit()
            return

        if title_text and message_text:
            _show_credentials_warning(
                dialog,
                title_text,
                message_text,
                bool(_charging_cache.get("prev")),
                card.width(),
            )

    class CredentialsDialogKeyFilter(QObject):
        def eventFilter(self, watched: QObject, event: QEvent) -> bool:
            if event.type() != QEvent.Type.KeyPress:
                return super().eventFilter(watched, event)
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                _handle_enter_key()
                event.accept()
                return True
            if key == Qt.Key.Key_Escape:
                dialog.reject()
                event.accept()
                return True
            return super().eventFilter(watched, event)

    username_input.returnPressed.connect(_handle_enter_key)
    password_input.returnPressed.connect(_handle_enter_key)
    credentials_key_filter = CredentialsDialogKeyFilter(dialog)
    dialog._credentials_key_filter = credentials_key_filter  # type: ignore[attr-defined]
    for key_widget in (dialog, card, username_input, password_input, toggle_password_btn, cancel_btn, submit_btn):
        key_widget.installEventFilter(credentials_key_filter)

    # --- Charging state: dark glass base with restrained cyan accents. ---
    try:
        from ui.battery_status import get_battery_info
    except ImportError:
        from src.ui.battery_status import get_battery_info  # type: ignore

    from PySide6.QtCore import QTimer
    _charging_cache: dict[str, bool | None] = {"prev": None}

    def _refresh_widget_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _read_charging_state() -> bool:
        info = get_battery_info()
        if os.getenv("CREDENTIALS_CHARGING_DEBUG") == "1":
            logger.debug("credentials charging info: %s", info)
        if not info:
            return bool(_charging_cache["prev"])
        charging = info.get("charging")
        if isinstance(charging, bool):
            return charging
        if isinstance(charging, int):
            return bool(charging)
        return bool(_charging_cache["prev"])

    def _apply_charging(charging: bool) -> None:
        dialog.set_charging_background(charging)
        card.set_charging(charging)
        dialog.setStyleSheet(_STYLE_CHARGING if charging else _STYLE_NORMAL)
        _refresh_widget_style(dialog)
        title.setText(_TITLE_CHARGING if charging else _TITLE_NORMAL)
        if isinstance(title.graphicsEffect(), QGraphicsDropShadowEffect):
            title_effect = title.graphicsEffect()
            title_effect.setBlurRadius(12 if charging else 11)
            title_effect.setColor(QColor(103, 224, 255, 54) if charging else QColor(255, 255, 255, 42))
        icon_color = QColor("#DDF7FF") if charging else QColor("#F4F8FF")
        check_color = QColor("#DDF7FF") if charging else QColor("#FFFFFF")
        eye_color = QColor("#DDF7FF") if charging else QColor("#F4F8FF")

        # Update icon colors
        _set_icon(username_icon, _draw_user_icon(18, icon_color))
        _set_icon(password_icon, _draw_lock_icon(18, icon_color))
        _set_icon(status_icon, _draw_check_icon(18, check_color, charging))
        # Ikuti status visibilitas password
        crossed = password_input.echoMode() == QLineEdit.EchoMode.Password
        toggle_password_btn.setIcon(QIcon(_draw_eye_icon(18, eye_color, crossed=crossed)))

        # Inline styles must also switch color; otherwise they override the dialog QSS.
        username_row.setProperty("charging", charging)
        password_row.setProperty("charging", charging)
        username_row.set_charging(charging)
        password_row.set_charging(charging)
        status_chip.set_charging(charging)
        field_label_color = "rgba(221, 247, 255, 0.92)" if charging else "rgba(244, 248, 255, 0.88)"
        status_label_color = "#FFFFFF" if charging else "#FFFFFF"
        field_label_style = (
            f"color: {field_label_color}; "
            "font-size: 13px; font-weight: 700; letter-spacing: 0.8px; "
            f"font-family: {CREDENTIALS_FONT_STACK};"
        )
        username_label.setStyleSheet(field_label_style)  # type: ignore
        password_label.setStyleSheet(field_label_style)  # type: ignore
        status_text.setStyleSheet(
            f"color: {status_label_color}; "
            f"font-size: 12px; font-weight: 500; font-family: {CREDENTIALS_FONT_STACK};"
        )  # type: ignore

        # Update glow/outline effect
        glow_color = QColor("#67E0FF" if charging else "#FFFFFF")
        glow_alpha = 38 if charging else 24
        for eff in [username_label.graphicsEffect(), password_label.graphicsEffect(), status_text.graphicsEffect()]:
            if isinstance(eff, QGraphicsDropShadowEffect):
                eff.setColor(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), glow_alpha))
                eff.setBlurRadius(6 if charging else 4)

        if isinstance(status_icon_glow, QGraphicsDropShadowEffect):
            status_icon_glow.setBlurRadius(5 if charging else 5)
            status_icon_glow.setColor(QColor(221, 247, 255, 30) if charging else QColor(255, 255, 255, 28))

        for eff in (username_row_shadow, password_row_shadow):
            focused = eff.parent() is not None and bool(getattr(eff.parent(), "property", lambda _: False)("focused"))
            eff.setBlurRadius((18 if focused else 13) if charging else (15 if focused else 11))
            eff.setOffset(0, 4 if focused else 3)
            if charging:
                eff.setColor(QColor(20, 126, 190, 86) if focused else QColor(3, 18, 36, 74))
            else:
                eff.setColor(QColor(255, 255, 255, 54) if focused else QColor(0, 0, 0, 58))

        if isinstance(status_chip_shadow, QGraphicsDropShadowEffect):
            status_chip_shadow.setBlurRadius(14 if charging else 12)
            status_chip_shadow.setOffset(0, 3)
            status_chip_shadow.setColor(QColor(3, 18, 36, 70) if charging else QColor(0, 0, 0, 54))

        _apply_action_button_theme(cancel_btn, submit_btn, charging)

        # Update card shadow
        parent_widget = card.parentWidget()
        if charging:
            card_shadow.setBlurRadius(24)
            card_shadow.setOffset(0, 9)
            card_shadow.setColor(QColor(3, 18, 36, 118))
            if parent_widget is not None:
                from PySide6.QtWidgets import QGraphicsEffect
                from typing import cast
                parent_widget.setGraphicsEffect(cast(QGraphicsEffect, None))
        else:
            card_shadow.setBlurRadius(16)
            card_shadow.setOffset(0, 7)
            card_shadow.setColor(QColor(0, 0, 0, 78))
            if parent_widget is not None:
                from PySide6.QtWidgets import QGraphicsEffect
                from typing import cast
                parent_widget.setGraphicsEffect(cast(QGraphicsEffect, None))

        # Update shimmer Top Glow sesuai charging
        if hasattr(top_glow, 'setCharging'):
            top_glow.setCharging(charging)

        for widget in (
            title,
            card,
            top_glow,
            username_label,
            username_row,
            username_icon,
            username_input,
            password_label,
            password_row,
            password_icon,
            password_input,
            toggle_password_btn,
            status_chip,
            status_icon,
            status_text,
            cancel_btn,
            submit_btn,
        ):
            _refresh_widget_style(widget)

        dialog.update()

    def _update_charging() -> None:
        charging = _read_charging_state()
        if _charging_cache["prev"] == charging:
            return
        if os.getenv("CREDENTIALS_CHARGING_DEBUG") == "1":
            logger.debug("credentials charging changed: %s -> %s", _charging_cache["prev"], charging)
        _charging_cache["prev"] = charging
        _apply_charging(charging)

    _charging_timer = QTimer(dialog)
    _charging_timer.timeout.connect(_update_charging)
    _charging_timer.start(500)
    _update_charging()  # update awal
    # -------------------------------------------------------------------

    password_input.setFocus()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result_user["user"]
    return None
