import logging
import math
import os
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QConicalGradient, QPainterPath, QRadialGradient, QPaintEvent, QLinearGradient, QBrush

logger = logging.getLogger(__name__)

BOOT_WIDTH = 405
BOOT_HEIGHT = int(18.5 * 0.3937 * 96)
BOOT_CORNER_RADIUS = 22.0
BOOT_DURATION_MS = 2500
BOOT_FADE_IN_MS = 260
BOOT_FADE_OUT_MS = 220
SPINNER_DIAMETER = 132
GLOBE_DIAMETER = 100
SPINNER_CHARGING_ROTATION_MS = 1680
SPINNER_IDLE_ROTATION_MS = 2300
SPINNER_CHARGING_ARC_MS = 1850
SPINNER_IDLE_ARC_MS = 2600
SPINNER_CHARGING_PULSE_MS = 2050
SPINNER_IDLE_PULSE_MS = 2850

class CircularProgress(QWidget):
    def __init__(self, diameter: int = 120, parent: QWidget | None = None):
        super().__init__(parent)
        self.diameter = diameter
        self.angle = 0
        self.base_thickness = 2.0
        self.amp_thickness = 0.22
        self.thickness = self.base_thickness
        self.charging = False
        self.pulse_period = SPINNER_IDLE_PULSE_MS
        self.rotation_period = SPINNER_IDLE_ROTATION_MS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(16)  # ~60 FPS
        self.setFixedSize(diameter, diameter)
        self._t = 0
        # Stroke dash animation
        self.arc_anim_period = SPINNER_IDLE_ARC_MS
        self.arc_min_span = 36       # degrees
        self.arc_max_span = 236      # degrees
        self.arc_start_angle = 0
        self.arc_span_angle = self.arc_min_span

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self.charging == charging:
            return
        self.charging = charging
        self._apply_motion_profile()
        self.update()

    def _apply_motion_profile(self) -> None:
        if self.charging:
            self.rotation_period = SPINNER_CHARGING_ROTATION_MS
            self.arc_anim_period = SPINNER_CHARGING_ARC_MS
            self.pulse_period = SPINNER_CHARGING_PULSE_MS
        else:
            self.rotation_period = SPINNER_IDLE_ROTATION_MS
            self.arc_anim_period = SPINNER_IDLE_ARC_MS
            self.pulse_period = SPINNER_IDLE_PULSE_MS

    def update_anim(self):
        self._t += 16
        # Circular Rotational Motion
        self.angle = (self.angle + 360 * 16 / self.rotation_period) % 360
        # Luxury breathing thickness
        phase = ((self._t % self.pulse_period) / self.pulse_period) * 2 * math.pi
        self.thickness = self.base_thickness + self.amp_thickness * math.sin(phase)
        # Stroke Dash Animation + Ease-in-out Curve
        arc_phase = ((self._t % self.arc_anim_period) / self.arc_anim_period)
        def ease_in_out(t: float) -> float:
            return 0.5 * (1 - math.cos(math.pi * t))
        if arc_phase < 0.5:
            eased = ease_in_out(arc_phase * 2)
            self.arc_span_angle = self.arc_min_span + (self.arc_max_span - self.arc_min_span) * eased
        else:
            eased = ease_in_out((1 - arc_phase) * 2)
            self.arc_span_angle = self.arc_min_span + (self.arc_max_span - self.arc_min_span) * eased
        self.arc_start_angle = (self.angle + 90 + 360 * arc_phase) % 360
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(self.thickness, self.thickness, self.diameter-2*self.thickness, self.diameter-2*self.thickness)
            halo_color = QColor(103, 224, 255, 26) if self.charging else QColor(255, 255, 255, 20)
            halo = QRadialGradient(rect.center(), self.diameter * 0.42)
            halo.setColorAt(0.0, halo_color)
            halo.setColorAt(0.56, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), max(3, halo_color.alpha() // 3)))
            halo.setColorAt(1.0, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(halo))
            painter.drawEllipse(rect.adjusted(14.0, 14.0, -14.0, -14.0))

            grad = QConicalGradient(rect.center(), -self.angle)
            if self.charging:
                transparent = QColor(62, 166, 255, 0)
                bright = QColor(103, 224, 255, 235)
                mid = QColor(80, 180, 255, 238)
                deep = QColor(55, 138, 238, 226)
                white = QColor(232, 250, 255, 220)
                glow_color = QColor(80, 180, 255, 34)
            else:
                transparent = QColor(255, 255, 255, 0)
                bright = QColor(255, 255, 255, 240)
                mid = QColor(238, 244, 250, 230)
                deep = QColor(205, 216, 228, 216)
                white = QColor(255, 255, 255, 224)
                glow_color = QColor(255, 255, 255, 30)
            grad.setColorAt(0.0, transparent)
            grad.setColorAt(0.24, bright)
            grad.setColorAt(0.46, mid)
            grad.setColorAt(0.68, deep)
            grad.setColorAt(0.86, white)
            grad.setColorAt(1.0, transparent)
            pen = QPen()
            pen.setBrush(grad)
            pen.setWidthF(self.thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            glow_pen = QPen(glow_color)
            glow_pen.setWidthF(self.thickness*1.5)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawArc(rect, int(self.arc_start_angle*16), int(self.arc_span_angle*16))
            # Draw main arc
            painter.setPen(pen)
            painter.drawArc(rect, int(self.arc_start_angle*16), int(self.arc_span_angle*16))
            # Draw shimmer highlight (arc shine)
            shimmer_pen = QPen(QColor(255, 255, 255, 150))
            shimmer_pen.setWidthF(self.thickness*0.55)
            shimmer_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(shimmer_pen)
            shimmer_start = self.arc_start_angle + self.arc_span_angle*0.18
            shimmer_span = self.arc_span_angle*0.13
            painter.drawArc(rect, int(shimmer_start*16), int(shimmer_span*16))
        except Exception:
            logger.exception("paintEvent CircularProgress failed")

# --- Glow mask widget with radial gradient ---
class GlowMaskWidget(QWidget):
    def __init__(self, child_widget: QWidget, diameter: int, glow_color: QColor = QColor(255,255,255,90), parent: QWidget | None = None):
        super().__init__(parent)
        self.child_widget = child_widget
        self.diameter = diameter
        self.glow_color = glow_color
        self.charging = False
        self._t = 0
        self.setFixedSize(diameter, diameter)
        self.child_widget.setParent(self)
        self.child_widget.move(0, 0)
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start(33)

    def _update_glow(self) -> None:
        self._t = (self._t + 33) % 2400
        self.update()

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self.charging == charging:
            return
        self.charging = charging
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        phase = (self._t / 2400.0) * 2.0 * math.pi
        pulse = 0.5 + 0.5 * math.sin(phase)
        if self.charging:
            core_alpha = int(26 + (8 * pulse))
            glow_alpha = int(54 + (22 * pulse))
            rim_alpha = int(96 + (26 * pulse))
            glow_core = QColor(232, 250, 255, core_alpha)
            glow_mid = QColor(103, 224, 255, glow_alpha)
            rim_color = QColor(103, 224, 255, rim_alpha)
            glow_edge = QColor(55, 138, 238, 0)
        else:
            core_alpha = int(20 + (6 * pulse))
            glow_alpha = int(40 + (14 * pulse))
            rim_alpha = int(66 + (18 * pulse))
            glow_core = QColor(255, 255, 255, core_alpha)
            glow_mid = QColor(255, 255, 255, glow_alpha)
            rim_color = QColor(238, 244, 250, rim_alpha)
            glow_edge = QColor(205, 216, 228, 0)

        shadow = QRadialGradient(self.diameter / 2, self.diameter * 0.66, self.diameter * 0.40)
        shadow.setColorAt(0.0, QColor(0, 0, 0, 48 if self.charging else 42))
        shadow.setColorAt(0.58, QColor(0, 0, 0, 16 if self.charging else 14))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(self.diameter * 0.16, self.diameter * 0.40, self.diameter * 0.68, self.diameter * 0.46))

        grad = QRadialGradient(self.diameter / 2, self.diameter / 2, self.diameter * 0.50)
        grad.setColorAt(0.0, glow_core)
        grad.setColorAt(0.58, glow_mid)
        grad.setColorAt(1.0, glow_edge)
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self.diameter, self.diameter)

        rim_rect = QRectF(3.0, 3.0, self.diameter - 6.0, self.diameter - 6.0)
        rim_gradient = QLinearGradient(rim_rect.left(), rim_rect.top(), rim_rect.left(), rim_rect.bottom())
        rim_gradient.setColorAt(0.0, QColor(rim_color.red(), rim_color.green(), rim_color.blue(), max(0, rim_color.alpha() - 20)))
        rim_gradient.setColorAt(0.52, QColor(rim_color.red(), rim_color.green(), rim_color.blue(), rim_color.alpha() // 3))
        rim_gradient.setColorAt(1.0, QColor(0, 0, 0, 34 if self.charging else 28))
        rim_pen = QPen(QBrush(rim_gradient), 0.85)
        rim_pen.setCosmetic(True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(rim_pen)
        painter.drawEllipse(rim_rect)
        # Child widget (globe) will be drawn automatically


class BreathingAnchorWidget(QWidget):
    def __init__(self, content_size: int, padding: int = 4, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = 1.0
        self._content_size = content_size
        self._padding = padding
        self.content = QWidget(self)
        self.content.setFixedSize(content_size, content_size)
        self.setFixedSize(content_size + (padding * 2), content_size + (padding * 2))
        self.content.move((self.width() - content_size) // 2, (self.height() - content_size) // 2)

    def get_scale(self) -> float:
        return self._scale

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.content.update()

    scale = Property(float, get_scale, set_scale)

# --- Main boot window ---
class AcrylicWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(BOOT_WIDTH, BOOT_HEIGHT)  # Samakan dengan lock.py
        self.setWindowOpacity(0.0)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self._background_corner_radius = BOOT_CORNER_RADIUS
        self._background_charging = False
        # Tempatkan window di tengah layar
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)
        # Background dilukis manual agar selaras dengan lock.py.
        self.setStyleSheet("""
            QDialog {
                background: transparent;
                border: none;
            }
            QLabel {
                color: white;
                font-family: 'SF Pro Display';
                font-size: 16px;
            }
        """)

        # Logo globe
        spinner_diameter = SPINNER_DIAMETER
        globe_diameter = GLOBE_DIAMETER
        logo_path = os.path.join(os.path.dirname(__file__), '../../assets/logo_splash.svg')
        self.anchor_widget = BreathingAnchorWidget(spinner_diameter, padding=4, parent=self)
        self.anchor_content = self.anchor_widget.content
        self.spinner = CircularProgress(diameter=spinner_diameter, parent=self.anchor_content)
        self.spinner.move(0, 0)
        if os.path.exists(logo_path):
            logo = QSvgWidget(logo_path, parent=self.anchor_content)
            logo.setFixedSize(globe_diameter, globe_diameter)
            globe_widget = GlowMaskWidget(logo, globe_diameter, glow_color=QColor(255,255,255,90), parent=self.anchor_content)
        else:
            globe_widget = QLabel("🌍", parent=self.anchor_content)
            globe_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            globe_widget.setStyleSheet("font-size: 48px; color: cyan;")
            globe_widget.setFixedSize(globe_diameter, globe_diameter)
        # Position globe at center of spinner
        globe_x = (spinner_diameter - globe_diameter) // 2
        globe_y = (spinner_diameter - globe_diameter) // 2
        globe_widget.setFixedSize(globe_diameter, globe_diameter)
        globe_widget.move(globe_x, globe_y)
        self.globe_widget = globe_widget

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(100)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addStretch(1)
        hbox.addWidget(self.anchor_widget)
        hbox.addStretch(1)
        layout.addLayout(hbox)
        layout.addStretch(122)
        self.setLayout(layout)
        self._breath_anim = None
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self.update_charging_state)
        self._charging_timer.start(200)
        self.update_charging_state()
        self._fade_in_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setDuration(BOOT_FADE_IN_MS)
        self._fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_out_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setDuration(BOOT_FADE_OUT_MS)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_out_anim.finished.connect(self.accept)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if getattr(self, '_fade_in_anim', None) is not None:
            self._fade_in_anim.stop()
            self.setWindowOpacity(0.0)
            self._fade_in_anim.start()

    def fade_out_and_accept(self) -> None:
        if getattr(self, '_fade_in_anim', None) is not None:
            self._fade_in_anim.stop()
        if getattr(self, '_fade_out_anim', None) is not None:
            self._fade_out_anim.stop()
            self._fade_out_anim.setStartValue(self.windowOpacity())
            self._fade_out_anim.start()
        else:
            self.accept()

    def update_charging_state(self) -> None:
        try:
            from ui.battery_status import get_battery_info
            info = get_battery_info()
            charging = bool(info.get('charging', False)) if info else False
        except Exception:
            charging = False
        if self._background_charging != charging:
            self._background_charging = charging
            self.update()
        if hasattr(self, 'spinner'):
            self.spinner.set_charging(charging)
        if hasattr(self, 'globe_widget') and hasattr(self.globe_widget, 'set_charging'):
            self.globe_widget.set_charging(charging)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        border_inset = 1.0
        rect = QRectF(border_inset, border_inset, self.width() - (border_inset * 2.0), self.height() - (border_inset * 2.0))
        radius = max(0.0, self._background_corner_radius - border_inset)
        charging = bool(getattr(self, '_background_charging', False))

        if charging:
            top_color = QColor(18, 30, 43)
            mid_color = QColor(31, 47, 64)
            bottom_color = QColor(20, 36, 55)
            accent_top = QColor(103, 224, 255, 38)
            accent_bottom = QColor(55, 138, 238, 20)
            focus_color = QColor(103, 224, 255, 34)
            lower_accent_color = QColor(55, 138, 238, 18)
            top_highlight_color = QColor(232, 250, 255, 36)
            border_top_color = QColor(232, 250, 255, 56)
            border_mid_color = QColor(103, 224, 255, 68)
            border_bottom_color = QColor(55, 138, 238, 28)
            inner_border_color = QColor(232, 250, 255, 31)
            second_inner_border_color = QColor(103, 224, 255, 18)
            edge_shadow_color = QColor(2, 12, 24, 27)
            lower_shadow = QColor(4, 16, 30, 46)
        else:
            top_color = QColor(26, 32, 41)
            mid_color = QColor(41, 49, 60)
            bottom_color = QColor(31, 39, 50)
            accent_top = QColor(255, 255, 255, 21)
            accent_bottom = QColor(205, 216, 228, 11)
            focus_color = QColor(255, 255, 255, 24)
            lower_accent_color = QColor(205, 216, 228, 10)
            top_highlight_color = QColor(255, 255, 255, 30)
            border_top_color = QColor(255, 255, 255, 49)
            border_mid_color = QColor(255, 255, 255, 43)
            border_bottom_color = QColor(205, 216, 228, 22)
            inner_border_color = QColor(255, 255, 255, 28)
            second_inner_border_color = QColor(205, 216, 228, 13)
            edge_shadow_color = QColor(0, 0, 0, 24)
            lower_shadow = QColor(0, 0, 0, 44)

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
        accent.setColorAt(0.60, QColor(accent_top.red(), accent_top.green(), accent_top.blue(), max(4, accent_top.alpha() // 3)))
        accent.setColorAt(1.0, accent_bottom)
        painter.setBrush(QBrush(accent))
        painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

        focus_glow = QRadialGradient(QPointF(rect.center().x(), rect.center().y() - 22.0), 170.0)
        focus_glow.setColorAt(0.0, focus_color)
        focus_glow.setColorAt(0.50, QColor(focus_color.red(), focus_color.green(), focus_color.blue(), max(3, focus_color.alpha() // 3)))
        focus_glow.setColorAt(1.0, QColor(focus_color.red(), focus_color.green(), focus_color.blue(), 0))
        painter.setBrush(QBrush(focus_glow))
        painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

        top_highlight = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + 22.0)
        top_highlight.setColorAt(0.0, top_highlight_color)
        top_highlight.setColorAt(1.0, QColor(top_highlight_color.red(), top_highlight_color.green(), top_highlight_color.blue(), 0))
        painter.setBrush(QBrush(top_highlight))
        painter.drawRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)

        lower_accent = QRadialGradient(QPointF(rect.center().x(), rect.bottom() - 8.0), 130.0)
        lower_accent.setColorAt(0.0, lower_accent_color)
        lower_accent.setColorAt(0.52, QColor(lower_accent_color.red(), lower_accent_color.green(), lower_accent_color.blue(), max(2, lower_accent_color.alpha() // 3)))
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

        bottom_depth = QLinearGradient(rect.left(), rect.bottom() - 32.0, rect.left(), rect.bottom())
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
        second_inner_rect = rect.adjusted(2.8, 2.8, -2.8, -2.8)
        second_inner_pen = QPen(second_inner_border_color, 0.45)
        second_inner_pen.setCosmetic(True)
        painter.setPen(second_inner_pen)
        painter.drawRoundedRect(second_inner_rect, radius - 2.8, radius - 2.8)

        border_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        border_gradient.setColorAt(0.0, border_top_color)
        border_gradient.setColorAt(0.46, border_mid_color)
        border_gradient.setColorAt(1.0, border_bottom_color)
        border_pen = QPen(QBrush(border_gradient), 1.0)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()


# --- Show boot dialog function ---
def show_boot():
    boot = AcrylicWindow()
    boot.setModal(True)
    from PySide6.QtGui import QGuiApplication
    screen = QGuiApplication.primaryScreen()
    screen_geometry = screen.geometry()
    width_px = boot.width()
    height_px = boot.height()
    boot.move(
        screen_geometry.x() + (screen_geometry.width() - width_px) // 2,
        screen_geometry.y() + (screen_geometry.height() - height_px) // 2
    )
    QTimer.singleShot(BOOT_DURATION_MS, boot.fade_out_and_accept)
    boot.exec()
