from importlib import import_module
from typing import Callable, Optional, Union, cast
from database.models import User
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QGridLayout, QLabel, QGraphicsDropShadowEffect, QApplication, QMessageBox
from PySide6.QtCore import Qt, Signal, QRectF, QEasingCurve, QPropertyAnimation, Property, QEvent, QPointF, QSize, QTimer
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QRadialGradient, QMouseEvent, QPaintEvent, QEnterEvent, QKeyEvent, QCloseEvent, QPainterPath
from PySide6.QtCore import QRect
from PySide6.QtGui import QLinearGradient
# Import widgets from lock.py
from ui.lock import BatteryLogoWidget, KeyCapWidget, GearIconWidget, WiFiLogoWidget, _hide_top_bar_tooltip, _paint_premium_padlock, _premium_tooltip_text, _show_top_bar_tooltip, show_lock

try:
    from ui.credentials_login import _show_credentials_warning
except ImportError:
    from src.ui.credentials_login import _show_credentials_warning  # type: ignore

AuthenticateFn = Callable[[str, str, object | None], User | None]
VerifyPinFn = Callable[[str], User | None]

try:
    _authenticate = import_module("auth.login").authenticate
except ImportError:
    _authenticate = import_module("src.auth.login").authenticate

authenticate = cast(AuthenticateFn, _authenticate)

try:
    _verify_pin_import = import_module("ui.flow_auth").verify_pin_step
except ImportError:
    _verify_pin_import = import_module("src.ui.flow_auth").verify_pin_step

_verify_pin = cast(VerifyPinFn, _verify_pin_import)

QSS_LABEL_STYLE = """
QLabel[charging="true"] {
    color: #50B4FF;
}
QLabel[charging="false"] {
    color: #FFFFFF;
}
"""


def _paint_pin_key_surface(
    painter: QPainter,
    rect: QRectF,
    charging: bool,
    hovered: bool,
    pressed: bool = False,
) -> None:
    """Paint a clean filled premium surface for PIN keypad controls."""
    lift = 0.75 if pressed else 0.0
    surface = rect.adjusted(3.0, 3.0 + lift, -3.0, -3.2 + lift)
    radius = surface.width() / 2.0

    if charging:
        center_color = QColor(34, 72, 96, 206)
        mid_color = QColor(16, 49, 74, 212)
        edge_color = QColor(5, 27, 49, 224)
        bevel_top = QColor(188, 244, 255, 46)
        bevel_bottom = QColor(1, 13, 28, 104)
        border_top = QColor(188, 244, 255, 68)
        border_bottom = QColor(40, 124, 210, 34)
        halo_color = QColor(80, 180, 255, 14)
        lower_shadow = QColor(2, 10, 22, 76)
    else:
        center_color = QColor(57, 66, 80, 206)
        mid_color = QColor(34, 43, 56, 212)
        edge_color = QColor(15, 24, 37, 224)
        bevel_top = QColor(255, 255, 255, 42)
        bevel_bottom = QColor(0, 0, 0, 104)
        border_top = QColor(255, 255, 255, 60)
        border_bottom = QColor(182, 194, 210, 24)
        halo_color = QColor(255, 255, 255, 10)
        lower_shadow = QColor(0, 0, 0, 76)

    if hovered:
        center_color.setAlpha(min(255, center_color.alpha() + 18))
        mid_color.setAlpha(min(255, mid_color.alpha() + 20))
        border_top.setAlpha(min(255, border_top.alpha() + 18))
        halo_color.setAlpha(min(255, halo_color.alpha() + 12))

    cast_shadow = QRadialGradient(surface.center() + QPointF(0.0, 2.8), radius * 0.96)
    cast_shadow.setColorAt(0.0, QColor(lower_shadow.red(), lower_shadow.green(), lower_shadow.blue(), max(12, lower_shadow.alpha() - 18)))
    cast_shadow.setColorAt(0.70, QColor(lower_shadow.red(), lower_shadow.green(), lower_shadow.blue(), max(8, lower_shadow.alpha() // 2)))
    cast_shadow.setColorAt(1.0, QColor(lower_shadow.red(), lower_shadow.green(), lower_shadow.blue(), 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(cast_shadow))
    painter.drawEllipse(surface.adjusted(0.6, 2.4, -0.6, 3.8))

    halo = QRadialGradient(surface.center(), radius * 1.02)
    halo.setColorAt(0.0, halo_color)
    halo.setColorAt(0.82, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), max(3, halo_color.alpha() // 3)))
    halo.setColorAt(1.0, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(halo))
    painter.drawEllipse(surface.adjusted(-1.2, -1.2, 1.2, 1.2))

    base = QRadialGradient(surface.center() + QPointF(-radius * 0.16, -radius * 0.22), radius * 1.18)
    base.setColorAt(0.0, center_color)
    base.setColorAt(0.58, mid_color)
    base.setColorAt(1.0, edge_color)
    painter.setBrush(QBrush(base))
    painter.drawEllipse(surface)

    bevel = QLinearGradient(surface.left(), surface.top(), surface.left(), surface.bottom())
    bevel.setColorAt(0.0, bevel_top)
    bevel.setColorAt(0.32, QColor(bevel_top.red(), bevel_top.green(), bevel_top.blue(), 0))
    bevel.setColorAt(0.72, QColor(bevel_bottom.red(), bevel_bottom.green(), bevel_bottom.blue(), 0))
    bevel.setColorAt(1.0, bevel_bottom)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QBrush(bevel), 1.15))
    painter.drawEllipse(surface.adjusted(1.1, 1.1, -1.1, -1.1))

    inner_pen = QPen(QColor(255, 255, 255, 16 if hovered else 11), 0.55)
    inner_pen.setCosmetic(True)
    painter.setPen(inner_pen)
    painter.drawEllipse(surface.adjusted(2.2, 2.2, -2.2, -2.2))

    border = QLinearGradient(surface.left(), surface.top(), surface.left(), surface.bottom())
    border.setColorAt(0.0, border_top)
    border.setColorAt(1.0, border_bottom)
    border_pen = QPen(QBrush(border), 0.88)
    border_pen.setCosmetic(True)
    painter.setPen(border_pen)
    painter.drawEllipse(surface)


class BackspaceButton(QWidget):
    """Custom backspace button with ⌫ icon in circular neumorphic style"""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.charging = False
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Animasi press effect
        self._scale = 1.0
        self._scale_anim = None
        self._hovering = False
    
    def set_charging(self, charging: bool) -> None:
        """Update charging status and trigger repaint"""
        self.charging = charging
        self.update()
    
    def get_scale(self) -> float:
        return self._scale
    
    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()
    
    scale = Property(float, get_scale, set_scale)
    
    def _animate_scale(self, start: float, end: float, duration: int = 150):
        # Stop and cleanup previous animation to prevent memory leak
        if self._scale_anim is not None:
            self._scale_anim.stop()
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim.deleteLater()
            self._scale_anim = None
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(lambda: self._cleanup_animation())
        self._scale_anim = anim
        anim.start()
    
    def _cleanup_animation(self) -> None:
        """Safely cleanup animation object"""
        if self._scale_anim is not None:
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim = None
    
    def trigger_press_animation(self) -> None:
        """Public method to trigger press animation from outside"""
        self._animate_scale(self._scale, 0.92, 100)
    
    def trigger_release_animation(self) -> None:
        """Public method to trigger release animation from outside"""
        self._animate_scale(self._scale, 1.0, 150)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 0.92, 100)
        super().mousePressEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovering = True
        self._animate_scale(self._scale, 1.025, 140)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovering = False
        self._animate_scale(self._scale, 1.0, 150)
        super().leaveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 1.0, 150)
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Backspace):
            self._animate_scale(self._scale, 0.92, 100)
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Backspace):
            self._animate_scale(self._scale, 1.0, 150)
        super().keyReleaseEvent(event)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Apply scale transformation untuk efek tenggelam/timbul
        w, h = self.width(), self.height()
        painter.save()
        painter.translate(w/2, h/2)
        painter.scale(self._scale, self._scale)
        painter.translate(-w/2, -h/2)
        
        # Lingkaran neumorphic sempurna (sama dengan RoundLabel)
        from PySide6.QtCore import QRectF
        
        center_x, center_y = 28.0, 28.0
        _paint_pin_key_surface(
            painter,
            QRectF(0.0, 0.0, float(w), float(h)),
            self.charging,
            bool(getattr(self, '_hovering', False)),
            self._scale < 0.98,
        )
        
        # Surface glass utama sudah membawa bevel, rim, dan depth.
        layers: list[dict[str, float]] = []
        if getattr(self, '_hovering', False):
            for layer in layers:
                layer['opacity_base'] += 7.0
                layer['opacity_max'] += 18.0
        
        # Gambar base circles untuk semua layer terlebih dahulu
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in layers:
            radius: float = layer['radius']
            opacity_base: float = layer['opacity_base']
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity_base)), 0.18, Qt.PenStyle.SolidLine))
            painter.drawEllipse(rect)
        
        # Dual-ridge neumorphic effect di seluruh lingkaran
        num_segments = 360
        
        # Pola ketebalan eksplisit untuk smooth transition
        thickness_pattern: list[float] = [
            0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
            0.55, 0.6, 0.65, 0.7,  # Peak
            0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.0
        ]
        
        pattern_length = len(thickness_pattern)
        ridge_peak_1 = 45.0
        ridge_peak_2 = 225.0
        ridge_half_width = 90.0
        
        # Tambahkan ridge effect untuk setiap layer
        for layer in layers:
            radius: float = layer['radius']
            scale: float = layer['scale']
            opacity_base: float = layer['opacity_base']
            opacity_max: float = layer['opacity_max']
            
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
            # Gambar efek ridge di seluruh 360 derajat
            for i in range(num_segments):
                current_angle = float(i)
                
                # Hitung distance angular dari kedua peaks
                def angular_distance(angle1: float, angle2: float) -> float:
                    diff = abs(angle1 - angle2)
                    return min(diff, 360.0 - diff)
                
                dist1 = angular_distance(current_angle, ridge_peak_1)
                dist2 = angular_distance(current_angle, ridge_peak_2)
                min_dist = min(dist1, dist2)
                
                # Area ridge dengan efek highlight
                if min_dist <= ridge_half_width:
                    progress = min_dist / ridge_half_width
                    peak_index = pattern_length // 2
                    pattern_index = int(peak_index - (peak_index * (1.0 - progress)))
                    pattern_index = max(0, min(pattern_length - 1, pattern_index))
                    
                    thickness: float = thickness_pattern[pattern_index] * scale
                    thickness_factor = thickness / (0.7 * scale) if scale > 0 else 0.0
                    opacity = int(opacity_base + (opacity_max - opacity_base) * thickness_factor)
                    if thickness > 0.01 and opacity > 15:
                        border_color = QColor(255, 255, 255, opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, thickness * 0.30, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
                else:
                    subtle_opacity = int(opacity_base * 0.4)
                    if subtle_opacity > 10:
                        border_color = QColor(255, 255, 255, subtle_opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, 0.10, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
        
        # Tentukan warna berdasarkan status charging
        if self.charging:
            icon_color = QColor(80, 180, 255, 232)
        else:
            icon_color = QColor(244, 248, 255, 232)
        
        # Gambar custom backspace icon: trapezoid + X mark
        # Ukuran dan posisi trapezoid - centered di lingkaran (28, 28)
        trap_width = 18.8
        trap_height = 12.8
        # Geser sedikit ke kanan untuk visual balance karena ada panah di kiri
        trap_center_x = 28.0 + 1.0  # Center lingkaran + offset visual balance
        trap_center_y = 28.0  # Center lingkaran
        
        # Hitung koordinat trapezoid (bentuk keyboard backspace)
        # Titik kiri atas
        tl_x = trap_center_x - trap_width / 2
        tl_y = trap_center_y - trap_height / 2
        # Titik kanan atas
        tr_x = trap_center_x + trap_width / 2
        tr_y = tl_y
        # Titik kanan bawah
        br_x = tr_x
        br_y = trap_center_y + trap_height / 2
        # Titik kiri bawah
        bl_x = tl_x
        bl_y = br_y
        # Titik ujung kiri (panah) - lebih jauh untuk ujung lebih runcing
        arrow_x = trap_center_x - trap_width / 2 - 5.0
        arrow_y = trap_center_y
        
        # Gambar trapezoid outline
        line_thickness = 0.78
        icon_pen = QPen(icon_color, line_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        icon_pen.setCosmetic(True)
        painter.setPen(icon_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Gunakan QPainterPath untuk rounded corners di sisi kanan
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        
        # Radius untuk rounded corner
        corner_radius = 2.5
        
        # Mulai dari kiri atas
        path.moveTo(QPointF(tl_x, tl_y))
        # Garis atas ke pojok kanan atas (sebelum rounded)
        path.lineTo(QPointF(tr_x - corner_radius, tr_y))
        # Rounded corner kanan atas
        path.arcTo(QRectF(tr_x - corner_radius * 2, tr_y, corner_radius * 2, corner_radius * 2), 90, -90)
        # Garis kanan (vertikal) dari setelah rounded atas ke sebelum rounded bawah
        path.lineTo(QPointF(br_x, br_y - corner_radius))
        # Rounded corner kanan bawah
        path.arcTo(QRectF(br_x - corner_radius * 2, br_y - corner_radius * 2, corner_radius * 2, corner_radius * 2), 0, -90)
        # Garis bawah
        path.lineTo(QPointF(bl_x, bl_y))
        # Kiri bawah ke ujung panah
        path.lineTo(QPointF(arrow_x, arrow_y))
        # Kiri atas ke awal (close path melalui ujung panah)
        path.lineTo(QPointF(tl_x, tl_y))
        
        # Gambar path
        painter.drawPath(path)
        
        # Gambar X mark di dalam trapezoid - centered di lingkaran
        x_size = 5.2
        x_center_x = 28.0 + 1.0  # Center lingkaran + offset visual balance (sama dengan trapezoid)
        x_center_y = 28.0  # Center lingkaran
        x_thickness = 0.82
        
        x_pen = QPen(icon_color, x_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        x_pen.setCosmetic(True)
        painter.setPen(x_pen)
        # Garis diagonal \ (kiri atas ke kanan bawah)
        painter.drawLine(
            QPointF(x_center_x - x_size / 2, x_center_y - x_size / 2),
            QPointF(x_center_x + x_size / 2, x_center_y + x_size / 2)
        )
        # Garis diagonal / (kiri bawah ke kanan atas)
        painter.drawLine(
            QPointF(x_center_x - x_size / 2, x_center_y + x_size / 2),
            QPointF(x_center_x + x_size / 2, x_center_y - x_size / 2)
        )
        
        painter.restore()
        painter.end()

class BackButton(QWidget):
    """Custom back button with home icon in circular neumorphic style"""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.charging = False
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Animasi press effect
        self._scale = 1.0
        self._scale_anim = None
        self._hovering = False
    
    def set_charging(self, charging: bool) -> None:
        """Update charging status and trigger repaint"""
        self.charging = charging
        self.update()
    
    def get_scale(self) -> float:
        return self._scale
    
    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()
    
    scale = Property(float, get_scale, set_scale)
    
    def _animate_scale(self, start: float, end: float, duration: int = 150):
        # Stop and cleanup previous animation to prevent memory leak
        if self._scale_anim is not None:
            self._scale_anim.stop()
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim.deleteLater()
            self._scale_anim = None
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(lambda: self._cleanup_animation())
        self._scale_anim = anim
        anim.start()
    
    def _cleanup_animation(self) -> None:
        """Safely cleanup animation object"""
        if self._scale_anim is not None:
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim = None
    
    def trigger_press_animation(self) -> None:
        """Public method to trigger press animation from outside"""
        self._animate_scale(self._scale, 0.92, 100)
    
    def trigger_release_animation(self) -> None:
        """Public method to trigger release animation from outside"""
        self._animate_scale(self._scale, 1.0, 150)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 0.92, 100)
        super().mousePressEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovering = True
        self._animate_scale(self._scale, 1.025, 140)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovering = False
        self._animate_scale(self._scale, 1.0, 150)
        super().leaveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 1.0, 150)
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Escape):
            self._animate_scale(self._scale, 0.92, 100)
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Escape):
            self._animate_scale(self._scale, 1.0, 150)
        super().keyReleaseEvent(event)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Apply scale transformation untuk efek tenggelam/timbul
        w, h = self.width(), self.height()
        painter.save()
        painter.translate(w/2, h/2)
        painter.scale(self._scale, self._scale)
        painter.translate(-w/2, -h/2)
        
        # Lingkaran neumorphic sempurna (sama dengan RoundLabel)
        from PySide6.QtCore import QRectF
        
        center_x, center_y = 28.0, 28.0
        _paint_pin_key_surface(
            painter,
            QRectF(0.0, 0.0, float(w), float(h)),
            self.charging,
            bool(getattr(self, '_hovering', False)),
            self._scale < 0.98,
        )
        
        # Surface glass utama sudah membawa bevel, rim, dan depth.
        layers: list[dict[str, float]] = []
        if getattr(self, '_hovering', False):
            for layer in layers:
                layer['opacity_base'] += 7.0
                layer['opacity_max'] += 18.0
        
        # Gambar base circles untuk semua layer terlebih dahulu
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in layers:
            radius: float = layer['radius']
            opacity_base: float = layer['opacity_base']
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity_base)), 0.18, Qt.PenStyle.SolidLine))
            painter.drawEllipse(rect)
        
        # Dual-ridge neumorphic effect di seluruh lingkaran
        num_segments = 360
        
        # Pola ketebalan eksplisit untuk smooth transition
        thickness_pattern: list[float] = [
            0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
            0.55, 0.6, 0.65, 0.7,  # Peak
            0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.0
        ]
        
        pattern_length = len(thickness_pattern)
        ridge_peak_1 = 45.0
        ridge_peak_2 = 225.0
        ridge_half_width = 90.0
        
        # Tambahkan ridge effect untuk setiap layer
        for layer in layers:
            radius: float = layer['radius']
            scale: float = layer['scale']
            opacity_base: float = layer['opacity_base']
            opacity_max: float = layer['opacity_max']
            
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
            # Gambar efek ridge di seluruh 360 derajat
            for i in range(num_segments):
                current_angle = float(i)
                
                # Hitung distance angular dari kedua peaks
                def angular_distance(angle1: float, angle2: float) -> float:
                    diff = abs(angle1 - angle2)
                    return min(diff, 360.0 - diff)
                
                dist1 = angular_distance(current_angle, ridge_peak_1)
                dist2 = angular_distance(current_angle, ridge_peak_2)
                min_dist = min(dist1, dist2)
                
                # Area ridge dengan efek highlight
                if min_dist <= ridge_half_width:
                    progress = min_dist / ridge_half_width
                    peak_index = pattern_length // 2
                    pattern_index = int(peak_index - (peak_index * (1.0 - progress)))
                    pattern_index = max(0, min(pattern_length - 1, pattern_index))
                    
                    thickness: float = thickness_pattern[pattern_index] * scale
                    thickness_factor = thickness / (0.7 * scale) if scale > 0 else 0.0
                    opacity = int(opacity_base + (opacity_max - opacity_base) * thickness_factor)
                    if thickness > 0.01 and opacity > 15:
                        border_color = QColor(255, 255, 255, opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, thickness * 0.30, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
                else:
                    subtle_opacity = int(opacity_base * 0.4)
                    if subtle_opacity > 10:
                        border_color = QColor(255, 255, 255, subtle_opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, 0.10, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
        
        # Tentukan warna berdasarkan status charging: biru saat charging, putih saat normal
        if self.charging:
            outline = QColor(80, 180, 255, 235)
            fill = QColor(80, 180, 255, 224)
        else:
            outline = QColor(244, 248, 255, 235)
            fill = QColor(244, 248, 255, 224)
        
        # Dimensi rumah - scaled untuk circular
        body_height = 9.5
        body_width = 16.0
        main_roof_gap = 0.0
        icon_vertical_offset = 0.0
        center_house_y = center_y
        
        # Center rumah SEMPURNA dalam circular (56x56, center: 28, 28)
        body_left_x = (w - body_width) / 2
        body_right_x = body_left_x + body_width
        
        # Geometri atap: alas bawah sama dengan body.
        import math
        triangle_base = body_width
        theta_puncak_deg = 120
        theta_puncak_rad = math.radians(theta_puncak_deg)
        upper_roof_overhang = 1.3
        # Secondary roof is drawn as a near-parallel outline of the main roof.
        # These values control a tight visual spacing.
        roof_outline_lift = 2.4
        roof_outline_apex_extra = 1.0
        triangle_height = (triangle_base / 2) / math.tan(theta_puncak_rad / 2)

        # Hitung posisi vertikal dari tinggi visual total ikon, agar center tepat di circular.
        alas_gap = body_height * 0.27
        top_offset = triangle_height
        bottom_offset = body_height + alas_gap
        body_top = center_house_y + ((top_offset - bottom_offset) / 2) + icon_vertical_offset
        body_bottom = body_top + body_height
        segitiga_top = body_top - triangle_height
        p_left = QPointF(body_left_x, body_top - main_roof_gap)
        p_right = QPointF(body_right_x, body_top - main_roof_gap)
        p_top = QPointF((body_left_x + body_right_x) / 2, segitiga_top)
        p2_left = QPointF(p_left.x() - upper_roof_overhang, p_left.y() - roof_outline_lift)
        p2_right = QPointF(p_right.x() + upper_roof_overhang, p_right.y() - roof_outline_lift)
        p2_top = QPointF(p_top.x(), p_top.y() - roof_outline_lift - roof_outline_apex_extra)
        
        pen_width = 0.86
        painter.setPen(QPen(outline, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        
        # Hitung pintu
        door_width = body_width * (8.5 / 24.9)
        door_height = body_height * 0.95
        door_x = body_left_x + (body_width - door_width) / 2
        door_y = body_bottom - door_height - 0.5
        door_rect = QRectF(door_x, door_y, door_width, door_height)
        
        # Body rumah
        body_rect = QRectF(body_left_x, body_top, body_width, body_height)

        # Fill rumah dibuat sebagai satu path utuh agar warna atap utama dan body merata.
        from PySide6.QtGui import QPainterPath
        house_fill_path = QPainterPath()
        house_fill_path.setFillRule(Qt.FillRule.OddEvenFill)
        house_fill_path.moveTo(body_left_x, body_bottom)
        house_fill_path.lineTo(body_left_x, body_top)
        house_fill_path.lineTo(p_top)
        house_fill_path.lineTo(body_right_x, body_top)
        house_fill_path.lineTo(body_right_x, body_bottom)
        house_fill_path.closeSubpath()
        house_fill_path.addRect(door_rect)

        painter.setBrush(QBrush(fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(house_fill_path)
        
        # Outline body tanpa garis atas agar tidak terlihat garis abu-abu membentang
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(fill, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        painter.drawLine(body_rect.topLeft(), body_rect.bottomLeft())
        painter.drawLine(body_rect.topRight(), body_rect.bottomRight())
        painter.drawLine(body_rect.bottomLeft(), body_rect.bottomRight())

        # Outline segitiga atas kedua
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outline, 0.44, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        painter.drawLine(p2_left, p2_top)
        painter.drawLine(p2_top, p2_right)

        # Isi atap segitiga dengan fill color — base diperluas ke body_top agar
        # tidak ada sisi bawah segitiga yang ter-render sebagai garis abu-abu
        p_fill_left = QPointF(body_left_x, body_top)
        p_fill_right = QPointF(body_right_x, body_top)
        painter.setBrush(QBrush(fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon([p_fill_left, p_top, p_fill_right])
        
        # Outline atap (segitiga)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(fill, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        painter.drawLine(p_left, p_top)
        painter.drawLine(p_top, p_right)
        
        # Alas rumah
        alas_offset = body_width * (4.0 / 24.9)
        alas_y = body_bottom + alas_gap
        left_bottom = QPointF(body_left_x - alas_offset, alas_y)
        right_bottom = QPointF(body_right_x + alas_offset, alas_y)
        painter.setPen(QPen(fill, 0.42, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        painter.drawLine(left_bottom, right_bottom)
        
        # Dinding kiri/kanan tetap terisi; garis atas body sengaja tidak digambar.
        
        # Pintu (hanya outline, tanpa fill)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outline, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        painter.drawLine(door_rect.topLeft(), door_rect.topRight())  # top
        painter.drawLine(door_rect.topLeft(), door_rect.bottomLeft())  # left
        painter.drawLine(door_rect.topRight(), door_rect.bottomRight())  # right
        
        painter.restore()
        painter.end()

class VerticalStretchLabel(QWidget):
    """Label dengan teks yang di-stretch vertikal tanpa mengubah lebar horizontal"""
    TOOLTIP_DURATION_MS = 850

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._text = ""
        self._charging = False
        self._scale = 1.0  # Scale proporsional (X dan Y)
        self._vertical_scale = 1.0  # Tetap untuk kompatibilitas
        self._scale_anim = None
        self._hovering = False
        self.setMinimumHeight(18)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("")
        self.setAccessibleDescription(self._state_tooltip_text())

    def _state_tooltip_text(self) -> str:
        time_text = self._text or "--.--"
        return f"Time : {time_text}"

    def _show_state_tooltip(self) -> None:
        tooltip_text = self._state_tooltip_text()
        _show_top_bar_tooltip(self, tooltip_text, self._charging, self.TOOLTIP_DURATION_MS)

    def get_scale(self) -> float:
        return self._scale

    def set_scale(self, value: float) -> None:
        self._scale = value
        self._vertical_scale = value  # Untuk kompatibilitas paintEvent lama
        self.update()

    scale = Property(float, get_scale, set_scale)

    def _animate_scale(self, start: float, end: float, duration: int = 180):
        if self._scale_anim is not None:
            self._scale_anim.stop()
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim.deleteLater()
            self._scale_anim = None
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(lambda: self._cleanup_animation())
        self._scale_anim = anim
        anim.start()

    def _cleanup_animation(self) -> None:
        if self._scale_anim is not None:
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim = None

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovering = True
        self._animate_scale(self._scale, 1.06, 180)
        self._show_state_tooltip()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovering = False
        self._animate_scale(self._scale, 1.0, 180)
        _hide_top_bar_tooltip(self)
        super().leaveEvent(event)
        
    def setText(self, text: str):
        self._text = text
        self.setAccessibleDescription(self._state_tooltip_text())
        if self._hovering:
            self._show_state_tooltip()
        self.update()
    
    def text(self) -> str:
        """Get current text"""
        return self._text
        
    def set_charging(self, charging: bool):
        self._charging = charging
        if self._hovering:
            self._show_state_tooltip()
        self.update()
        
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if getattr(self, '_hovering', False):
            glow_color = QColor(80, 180, 255, 30) if self._charging else QColor(255, 255, 255, 16)
            glow = QRadialGradient(QPointF(self.width() / 2, self.height() / 2), min(self.width(), self.height()) * 0.62)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(0.70, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(4, glow_color.alpha() // 3)))
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(QRectF(0.5, 2.0, self.width() - 1.0, self.height() - 4.0), 5.0, 5.0)
        # Setup font
        from PySide6.QtGui import QFont, QFontMetrics
        font = QFont()
        font.setFamily('IBM Plex Mono')
        if not QFontMetrics(font).inFont('0'):
            font.setFamily('Fira Mono')
        font.setWeight(QFont.Weight.ExtraLight if hasattr(QFont.Weight, 'ExtraLight') else QFont.Weight.Thin)
        font.setPointSizeF(18.1)
        font.setStretch(QFont.Stretch.Condensed)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.35)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(self._text)
        text_height = metrics.height()
        # Save state dan apply transform
        painter.save()
        # Pindah ke tengah widget
        center_x = self.width() / 2
        center_y = self.height() / 2
        painter.translate(center_x, center_y)
        # Scale proporsional (X dan Y)
        painter.scale(self._scale, self._scale)
        x = -text_width / 2
        y = text_height / 2 - metrics.descent()
        text_path = QPainterPath()
        text_path.addText(QPointF(x, y), font, self._text)
        bounds = text_path.boundingRect()
        if self._charging:
            top_color = QColor(103, 224, 255, 238)
            mid_color = QColor(80, 180, 255, 228)
            bottom_color = QColor(55, 138, 238, 218)
            shadow_color = QColor(18, 70, 130, 58)
            highlight_color = QColor(232, 250, 255, 34)
        else:
            top_color = QColor(255, 255, 255, 234)
            mid_color = QColor(238, 244, 250, 222)
            bottom_color = QColor(205, 216, 228, 214)
            shadow_color = QColor(0, 0, 0, 54)
            highlight_color = QColor(255, 255, 255, 30)
        shadow_path = QPainterPath(text_path)
        shadow_path.translate(0.0, 0.65)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawPath(shadow_path)
        grad = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.bottom())
        grad.setColorAt(0.0, top_color)
        grad.setColorAt(0.52, mid_color)
        grad.setColorAt(1.0, bottom_color)
        painter.setBrush(QBrush(grad))
        painter.drawPath(text_path)
        highlight_path = QPainterPath(text_path)
        highlight_path.translate(0.0, -0.30)
        painter.setBrush(QBrush(highlight_color))
        painter.drawPath(highlight_path)
        painter.restore()

class RoundLabel(QLabel):
    def __init__(self, text: str = '', parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.number_text = text
        self.charging = False
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Enable keyboard focus
        
        # Mapping angka ke alfabet (standar keypad telefon)
        self.alphabet_map = {
            '2': 'A B C',
            '3': 'D E F',
            '4': 'G H I',
            '5': 'J K L',
            '6': 'M N O',
            '7': 'P Q R S',
            '8': 'T U V',
            '9': 'W X Y Z'
        }
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet('''
            QLabel {
                background: transparent;
                border: none;
                color: #1a2233;
                font-family: 'SF Pro Display', 'Segoe UI', Arial, sans-serif;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel:pressed {
                background: rgba(224, 231, 239, 0.3);
            }
        ''')
        
        # Animasi press effect
        self._scale = 1.0
        self._scale_anim = None
    
    def set_charging(self, charging: bool) -> None:
        """Update charging status and trigger repaint"""
        self.charging = charging
        self.update()
    
    def get_scale(self) -> float:
        return self._scale
    
    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()
    
    scale = Property(float, get_scale, set_scale)
    
    def _animate_scale(self, start: float, end: float, duration: int = 150):
        # Stop and cleanup previous animation to prevent memory leak
        if self._scale_anim is not None:
            self._scale_anim.stop()
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim.deleteLater()
            self._scale_anim = None
        
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(lambda: self._cleanup_animation())
        self._scale_anim = anim
        anim.start()
    
    def _cleanup_animation(self) -> None:
        """Safely cleanup animation object"""
        if self._scale_anim is not None:
            try:
                self._scale_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._scale_anim = None
    
    def trigger_press_animation(self) -> None:
        """Public method to trigger press animation from outside"""
        self._animate_scale(self._scale, 0.92, 100)
    
    def trigger_release_animation(self) -> None:
        """Public method to trigger release animation from outside"""
        self._animate_scale(self._scale, 1.0, 150)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 0.92, 100)
        super().mousePressEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovering = True
        self._animate_scale(self._scale, 1.025, 140)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovering = False
        self._animate_scale(self._scale, 1.0, 150)
        super().leaveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Timbul kembali ke 1.0
            self._animate_scale(self._scale, 1.0, 150)
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._animate_scale(self._scale, 0.92, 100)
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            # Timbul kembali ke 1.0
            self._animate_scale(self._scale, 1.0, 150)
        super().keyReleaseEvent(event)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Apply scale transformation untuk efek tenggelam/timbul
        w, h = self.width(), self.height()
        painter.save()
        painter.translate(w/2, h/2)
        painter.scale(self._scale, self._scale)
        painter.translate(-w/2, -h/2)
        
        # Lingkaran neumorphic sempurna dengan full coverage
        from PySide6.QtCore import QRectF
        
        center_x, center_y = 28.0, 28.0
        _paint_pin_key_surface(
            painter,
            QRectF(0.0, 0.0, float(w), float(h)),
            self.charging,
            bool(getattr(self, '_hovering', False)),
            self._scale < 0.98,
        )
        
        # Surface glass utama sudah membawa bevel, rim, dan depth.
        layers: list[dict[str, float]] = []
        if getattr(self, '_hovering', False):
            for layer in layers:
                layer['opacity_base'] += 7.0
                layer['opacity_max'] += 18.0
        
        # Gambar base circles untuk semua layer terlebih dahulu
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in layers:
            radius: float = layer['radius']
            opacity_base: float = layer['opacity_base']
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity_base)), 0.18, Qt.PenStyle.SolidLine))
            painter.drawEllipse(rect)
        
        # Dual-ridge neumorphic effect di seluruh lingkaran
        num_segments = 360
        
        # Pola ketebalan eksplisit untuk smooth transition
        thickness_pattern: list[float] = [
            0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
            0.55, 0.6, 0.65, 0.7,  # Peak
            0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.0
        ]
        
        pattern_length = len(thickness_pattern)
        ridge_peak_1 = 45.0
        ridge_peak_2 = 225.0
        ridge_half_width = 90.0
        
        # Tambahkan ridge effect untuk setiap layer
        for layer in layers:
            radius: float = layer['radius']
            scale: float = layer['scale']
            opacity_base: float = layer['opacity_base']
            opacity_max: float = layer['opacity_max']
            
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
            # Gambar efek ridge di seluruh 360 derajat
            for i in range(num_segments):
                current_angle = float(i)
                
                # Hitung distance angular dari kedua peaks
                def angular_distance(angle1: float, angle2: float) -> float:
                    diff = abs(angle1 - angle2)
                    return min(diff, 360.0 - diff)
                
                dist1 = angular_distance(current_angle, ridge_peak_1)
                dist2 = angular_distance(current_angle, ridge_peak_2)
                min_dist = min(dist1, dist2)
                
                # Area ridge dengan efek highlight
                if min_dist <= ridge_half_width:
                    progress = min_dist / ridge_half_width
                    peak_index = pattern_length // 2
                    pattern_index = int(peak_index - (peak_index * (1.0 - progress)))
                    pattern_index = max(0, min(pattern_length - 1, pattern_index))
                    
                    thickness: float = thickness_pattern[pattern_index] * scale
                    thickness_factor = thickness / (0.7 * scale) if scale > 0 else 0.0
                    opacity = int(opacity_base + (opacity_max - opacity_base) * thickness_factor)
                    if thickness > 0.01 and opacity > 15:
                        border_color = QColor(255, 255, 255, opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, thickness * 0.30, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
                else:
                    # Area di luar ridge tetap ada subtle outline
                    subtle_opacity = int(opacity_base * 0.4)
                    if subtle_opacity > 10:
                        border_color = QColor(255, 255, 255, subtle_opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, 0.10, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
        
        # Hitung posisi vertikal yang seimbang
        from PySide6.QtGui import QFont
        
        if self.number_text in self.alphabet_map:
            number_offset = -5
            alphabet_offset = 11
        else:
            number_offset = 0
            alphabet_offset = 0
        
        # Tentukan warna berdasarkan status charging
        if self.charging:
            text_color = QColor(80, 180, 255, 246)
        else:
            text_color = QColor(244, 248, 255, 242)
        
        # Gambar angka
        number_font = QFont()
        number_font.setFamilies(['SF Pro Display', 'SF Pro Text', 'Segoe UI', 'Arial'])
        number_font.setPointSize(17)
        number_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(number_font)
        painter.setPen(text_color)
        
        number_rect = self.rect().adjusted(0, number_offset, 0, number_offset)
        painter.drawText(number_rect, Qt.AlignmentFlag.AlignCenter, self.number_text)
        
        # Gambar alfabet di bawah (jika ada)
        if self.number_text in self.alphabet_map:
            alphabet_text = self.alphabet_map[self.number_text]
            alphabet_font = QFont()
            alphabet_font.setFamilies(['SF Pro Display', 'SF Pro Text', 'Segoe UI', 'Arial'])
            alphabet_font.setPointSize(4)
            alphabet_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(alphabet_font)
            
            alphabet_rect = self.rect().adjusted(0, alphabet_offset, 0, alphabet_offset)
            painter.drawText(alphabet_rect, Qt.AlignmentFlag.AlignCenter, alphabet_text)
        
        painter.restore()  # Restore painter state
        painter.end()

def authenticate_typed(username: str, password: str, session: Optional[object] = None) -> Optional[User]:
    return authenticate(username, password, session)
# CustomUnlockIcon: Widget logo gembok unlock, identik dengan CustomLockIcon, hanya shackle kanan terbuka

class CustomUnlockIcon(QWidget):
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        W, H = self.width(), self.height()
        painter.translate(W/2, H/2)
        painter.scale(getattr(self, '_scale', 1.0), getattr(self, '_scale', 1.0))
        painter.translate(-W/2, -H/2)
        _paint_premium_padlock(
            painter,
            QRectF(0.0, 0.0, float(W), float(H)),
            charging=self.charging,
            unlocked=True,
            hovering=getattr(self, '_hovering', False),
            lock_color=self.lock_color if hasattr(self, 'lock_color') else QColor(255, 255, 255),
        )

    clicked = Signal()

    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    scale = Property(float, get_scale, set_scale)

    def __init__(self, color: QColor = QColor(255, 255, 255), parent: Optional[QWidget] = None, charging: bool = False):
        super().__init__(parent)
        self.lock_color = color
        self.original_color = color
        self.setFixedSize(64, 64)
        self.setToolTip("")
        self.setAccessibleDescription("Login")
        self.battery_widget = None
        self._shackle_anim = None
        self._shackle_angle = 180  # degrees, open
        self._on_shackle_closed = None
        self._shackle_open = True
        self.charging = charging
        self._hovering = False
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._update_charging_status)
        self._charging_timer.start(200)

    def set_battery_widget(self, battery_widget: Optional[QWidget]) -> None:
        self.battery_widget = battery_widget
        self._update_charging_status()

    def _update_charging_status(self) -> None:
        charging = False
        if self.battery_widget is not None:
            charging = bool(getattr(self.battery_widget, 'charging', False))
        if charging != self.charging:
            self.charging = charging
            if self._hovering:
                _show_top_bar_tooltip(self, _premium_tooltip_text(self, "Login"), self.charging)
            self.update()

    def set_charging(self, charging: bool):
        self.charging = charging
        if self._hovering:
            _show_top_bar_tooltip(self, _premium_tooltip_text(self, "Login"), self.charging)
        self.update()

    def enterEvent(self, event: QEnterEvent):
        self._hovering = True
        # Cleanup old animation
        old_anim = getattr(self, '_scale_anim', None)
        if old_anim is not None:
            try:
                old_anim.stop()
                old_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
        
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.0))
        self._scale_anim.setEndValue(1.08)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        _show_top_bar_tooltip(self, _premium_tooltip_text(self, "Login"), self.charging)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self._hovering = False
        self.update()
        self.animate_to_normal()
        self.unsetCursor()
        _hide_top_bar_tooltip(self)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self.animate_to_normal()
            self.clicked.emit()
        super().mousePressEvent(event)

    def animate_shackle_close(self):
        # Animate shackle arc from open (180 deg) to closed (160 deg)
        from PySide6.QtCore import QPropertyAnimation
        # Cleanup old animation
        old_anim = getattr(self, '_shackle_anim', None)
        if old_anim is not None:
            try:
                old_anim.stop()
                old_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
        
        self._shackle_anim = QPropertyAnimation(self, b"shackle_angle")
        self._shackle_anim.setStartValue(180)
        self._shackle_anim.setDuration(320)
        self._shackle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._shackle_anim.valueChanged.connect(self.update)
        def finish():
            self._shackle_open = False
            self.update()
            if self._on_shackle_closed:
                self._on_shackle_closed()
        self._shackle_anim.finished.connect(finish)
        self._shackle_anim.start()

    def get_shackle_angle(self):
        return getattr(self, '_shackle_angle', 180)

    def set_shackle_angle(self, value: float):
        self._shackle_angle = value
        self.update()


    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.animate_to_normal()
        self.clicked.emit()
        super().mouseDoubleClickEvent(event)

    def animate_to_normal(self):
        # Cleanup old animation
        old_anim = getattr(self, '_scale_anim', None)
        if old_anim is not None:
            try:
                old_anim.stop()
                old_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
        
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.08))
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()

GLASS_STYLE = """
QDialog {
    background: transparent;
    border: none;
}
"""

class UnlockIconWidget(QWidget):
    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    scale = Property(float, get_scale, set_scale)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(int(63.5), int(63.5))
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(15)
        effect.setColor(QColor(0, 0, 0, 80))
        effect.setOffset(0, 4)
        self.setGraphicsEffect(effect)
        self.hovered = False

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # Glassmorphism gradient
        center = QPointF(self.width() / 2, self.height() / 2)
        gradient = QRadialGradient(center, self.width() / 2, center)
        gradient.setColorAt(0, QColor(255, 255, 255, 180))
        gradient.setColorAt(1, QColor(100, 100, 180, 80))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        # Body gembok
        W, H = self.width(), self.height()
        margin_x, margin_y = 8, 5
        padlock_w = W - 2 * margin_x
        body_width = int(padlock_w * 0.32)
        body_height = int((H - 2 * margin_y) * 0.20)
        body_x = margin_x + (padlock_w - body_width) // 2
        body_y = margin_y + (H - 2 * margin_y) - body_height - 4
        painter.setPen(QColor(80, 80, 180, 200))
        painter.drawRoundedRect(int(body_x), int(body_y), int(body_width), int(body_height), 3, 3)
        # Shackle terbuka
        shackle_width = int(body_width * 0.6)
        shackle_height = int(body_height * 0.85)
        shackle_x = body_x + (body_width - shackle_width) // 2
        shackle_y = body_y - shackle_height + 2
        shackle_rect = QRectF(shackle_x, shackle_y, shackle_width, shackle_height)
        # Arc shackle (hanya 3/4 lingkaran, ujung kanan terbuka)
        painter.setPen(QColor(80, 80, 180, 200))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(shackle_rect, 30 * 16, 210 * 16)  # arc dari kiri ke atas, kanan terbuka
        # Garis kaki kiri shackle ke body
        painter.drawLine(
            int(shackle_x + 2),
            int(body_y),
            int(shackle_x + 2),
            int(shackle_y + int(shackle_height // 2))
        )
        # Ujung kanan shackle dibiarkan terbuka (tidak ada garis ke body)
        # Glow saat hover
        if self.hovered:
            painter.setBrush(QColor(180, 220, 255, 60))
            painter.drawEllipse(5, 5, 55, 55)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Aksi: buka form lock dan tutup login
            parent = self.parent()
            if hasattr(parent, 'open_lock_form'):
                parent.open_lock_form()  # type: ignore[attr-defined]

    def enterEvent(self, event: QEvent):
        self.hovered = True
        self.update()
        parent = self.parentWidget()
        charging = bool(getattr(parent, "_background_charging", False)) if parent is not None else False
        _show_top_bar_tooltip(self, _premium_tooltip_text(self, "Login"), charging)

    def leaveEvent(self, event: QEvent):
        self.hovered = False
        self.update()
        _hide_top_bar_tooltip(self)

class HomeButton(QWidget):
    clicked = Signal()

    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    scale = Property(float, get_scale, set_scale)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(48, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("")
        self.setAccessibleDescription("Kembali ke Home")
        self._hover = False
    def enterEvent(self, event: QEnterEvent) -> None:
        self._hover = True
        self.update()
        parent = self.parentWidget()
        charging = bool(getattr(parent, "_background_charging", False)) if parent is not None else False
        _show_top_bar_tooltip(self, _premium_tooltip_text(self, "Kembali ke Home"), charging)
        super().enterEvent(event)
    def leaveEvent(self, event: QEvent) -> None:
        self._hover = False
        self.update()
        _hide_top_bar_tooltip(self)
        super().leaveEvent(event)
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        margin = 9
        outline = QColor(255, 255, 255)
        # Atap segitiga (outline saja)
        roof_top = margin
        # roof_left dan roof_right dihapus karena tidak digunakan
        roof_bottom = h * 0.5
        pen = QPen(outline, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Dinding kotak (outline saja)
        body_top = roof_bottom
        body_height = h - body_top - margin
        body_width = w - 2 * margin
        body_rect = QRectF(margin, body_top, body_width, body_height)
        # Atap segitiga menyatu dengan persegi: alas segitiga di atas kiri dan kanan persegi
        segitiga_left = body_rect.left()
        segitiga_right = body_rect.right()
        segitiga_top = roof_top
        left_point = QPointF(segitiga_left, body_rect.top())
        top_point = QPointF(w / 2, segitiga_top)
        right_point = QPointF(segitiga_right, body_rect.top())
        right_bottom = body_rect.bottomRight()
        left_bottom = body_rect.bottomLeft()

        # Draw a single contiguous outline to avoid seam artifacts at segment joins.
        from PySide6.QtGui import QPainterPath
        house_path = QPainterPath()
        house_path.moveTo(left_point)
        house_path.lineTo(top_point)
        house_path.lineTo(right_point)
        house_path.lineTo(right_bottom)
        house_path.lineTo(left_bottom)
        house_path.lineTo(left_point)
        painter.drawPath(house_path)


class LoginDialog(QDialog):
    home_btn: Optional[QWidget] = None

    def closeEvent(self, event: QCloseEvent):
        # Cleanup timer dan resource lain agar tidak menumpuk saat dialog dibuka ulang
        if hasattr(self, 'charging_timer') and self.charging_timer is not None:
            try:
                self.charging_timer.stop()
                self.charging_timer.timeout.disconnect()
            except Exception:
                pass
            self.charging_timer = None
        super().closeEvent(event)

    def __init__(self: 'LoginDialog', parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.unlock_icon: Optional[CustomUnlockIcon] = None
        self.authenticated_user: Optional[User] = None
        self.request_back_to_lock: bool = False
        self.security_pin_logged: bool = False
        self._background_charging = False
        self._background_corner_radius = 22.0
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.keypad_map: dict[str, Optional[Union[RoundLabel, BackspaceButton, BackButton]]] = {}  # Map angka/backspace/back ke widget

    def set_background_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._background_charging == charging:
            return
        self._background_charging = charging
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        border_inset = 1.0
        corner_radius = float(getattr(self, '_background_corner_radius', 22.0))
        rect = QRectF(border_inset, border_inset, self.width() - (border_inset * 2.0), self.height() - (border_inset * 2.0))
        radius = max(0.0, corner_radius - border_inset)
        charging = bool(getattr(self, '_background_charging', False))

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

        focus_glow = QRadialGradient(QPointF(rect.center().x(), rect.top() + 42.0), 178.0)
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
        painter.end()

    def get_scale(self):
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float):
        self._scale = value
        self.update()

    from PySide6.QtCore import Property
    scale = Property(float, get_scale, set_scale)

class PINDotWidget(QWidget):
    """Custom widget to display 6 PIN dots visually"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(200, 34)
        self.pin_count = 0
        self.is_complete = False
        self.charging = False
        self._previous_pin_count = 0
        self._pop_index = -1
        self._pop_scale = 1.0
        self._pop_anim = None
        self._shrink_index = -1
        self._shrink_count = 0
        self._shrink_scale = 1.0
        self._shrink_anim = None
        self._error_pulse = 0.0
        self._error_anim = None
        
    def set_pin_count(self, count: int) -> None:
        """Update number of filled dots (0-6)"""
        next_count = min(max(count, 0), 6)
        if next_count > self.pin_count:
            self._start_pop(next_count - 1)
        elif next_count < self.pin_count:
            self._start_shrink(self.pin_count - 1, next_count)
            return
        self._previous_pin_count = self.pin_count
        self.pin_count = next_count
        self.is_complete = (self.pin_count == 6)
        self.update()

    def get_pop_scale(self) -> float:
        return self._pop_scale

    def set_pop_scale(self, value: float) -> None:
        self._pop_scale = value
        self.update()

    pop_scale = Property(float, get_pop_scale, set_pop_scale)

    def get_shrink_scale(self) -> float:
        return self._shrink_scale

    def set_shrink_scale(self, value: float) -> None:
        self._shrink_scale = value
        self.update()

    shrink_scale = Property(float, get_shrink_scale, set_shrink_scale)

    def get_error_pulse(self) -> float:
        return self._error_pulse

    def set_error_pulse(self, value: float) -> None:
        self._error_pulse = value
        self.update()

    error_pulse = Property(float, get_error_pulse, set_error_pulse)

    def _start_pop(self, index: int) -> None:
        if self._pop_anim is not None:
            self._pop_anim.stop()
            try:
                self._pop_anim.valueChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._pop_anim.deleteLater()
            self._pop_anim = None
        self._pop_index = index
        self._pop_scale = 1.0
        anim = QPropertyAnimation(self, b"pop_scale")
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.45, 1.18)
        anim.setEndValue(1.0)
        anim.setDuration(125)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(self._finish_pop)
        self._pop_anim = anim
        anim.start()

    def _finish_pop(self) -> None:
        self._pop_index = -1
        self._pop_scale = 1.0
        if self._pop_anim is not None:
            try:
                self._pop_anim.valueChanged.disconnect()
                self._pop_anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._pop_anim = None
        self.update()

    def trigger_error_pulse(self) -> None:
        if self._error_anim is not None:
            self._error_anim.stop()
            try:
                self._error_anim.valueChanged.disconnect()
                self._error_anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._error_anim.deleteLater()
            self._error_anim = None
        self._error_pulse = 0.0
        anim = QPropertyAnimation(self, b"error_pulse")
        anim.setStartValue(0.0)
        anim.setKeyValueAt(0.35, 1.0)
        anim.setEndValue(0.0)
        anim.setDuration(360)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(self._finish_error_pulse)
        self._error_anim = anim
        anim.start()

    def _finish_error_pulse(self) -> None:
        self._error_pulse = 0.0
        if self._error_anim is not None:
            try:
                self._error_anim.valueChanged.disconnect()
                self._error_anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._error_anim = None
        self.update()

    def _start_shrink(self, index: int, next_count: int) -> None:
        if self._shrink_anim is not None:
            self._shrink_anim.stop()
            try:
                self._shrink_anim.valueChanged.disconnect()
                self._shrink_anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._shrink_anim.deleteLater()
            self._shrink_anim = None
        self._shrink_index = index
        self._shrink_count = next_count
        self._shrink_scale = 1.0
        anim = QPropertyAnimation(self, b"shrink_scale")
        anim.setStartValue(1.0)
        anim.setEndValue(0.58)
        anim.setDuration(96)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(self._finish_shrink)
        self._shrink_anim = anim
        anim.start()

    def _finish_shrink(self) -> None:
        self._previous_pin_count = self.pin_count
        self.pin_count = self._shrink_count
        self.is_complete = (self.pin_count == 6)
        self._shrink_index = -1
        self._shrink_count = self.pin_count
        self._shrink_scale = 1.0
        if self._shrink_anim is not None:
            try:
                self._shrink_anim.valueChanged.disconnect()
                self._shrink_anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._shrink_anim = None
        self.update()
        
    def set_charging(self, charging: bool) -> None:
        """Update charging status and trigger repaint"""
        self.charging = charging
        self.update()
        
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        dot_size = 13.2
        spacing = 15.0
        total_width = (dot_size * 6) + (spacing * 5)
        start_x = (self.width() - total_width) / 2.0
        center_y = self.height() / 2.0
        
        if self.charging:
            top_color = QColor(103, 224, 255, 245)
            bottom_color = QColor(55, 138, 238, 232)
            border_color = QColor(103, 224, 255, 160)
            empty_border = QColor(103, 224, 255, 104)
            shadow_color = QColor(22, 84, 145, 72)
            highlight_color = QColor(232, 250, 255, 62)
        else:
            top_color = QColor(255, 255, 255, 244)
            bottom_color = QColor(205, 216, 228, 230)
            border_color = QColor(255, 255, 255, 145)
            empty_border = QColor(255, 255, 255, 98)
            shadow_color = QColor(0, 0, 0, 56)
            highlight_color = QColor(255, 255, 255, 48)
        pulse = max(0.0, min(1.0, self._error_pulse))
        if pulse > 0.0:
            if self.charging:
                error_border = QColor(255, 198, 104, int(118 * pulse))
                error_fill_top = QColor(255, 215, 135, int(86 * pulse))
                error_shadow = QColor(120, 64, 18, int(48 * pulse))
            else:
                error_border = QColor(255, 222, 166, int(112 * pulse))
                error_fill_top = QColor(255, 236, 205, int(62 * pulse))
                error_shadow = QColor(90, 48, 14, int(42 * pulse))
            empty_border = QColor(
                min(255, int(empty_border.red() * (1.0 - pulse) + error_border.red() * pulse)),
                min(255, int(empty_border.green() * (1.0 - pulse) + error_border.green() * pulse)),
                min(255, int(empty_border.blue() * (1.0 - pulse) + error_border.blue() * pulse)),
                min(255, int(empty_border.alpha() + error_border.alpha())),
            )
            border_color = QColor(
                min(255, int(border_color.red() * (1.0 - pulse) + error_border.red() * pulse)),
                min(255, int(border_color.green() * (1.0 - pulse) + error_border.green() * pulse)),
                min(255, int(border_color.blue() * (1.0 - pulse) + error_border.blue() * pulse)),
                min(255, int(border_color.alpha() + error_border.alpha() * 0.55)),
            )
            top_color = QColor(
                min(255, int(top_color.red() * (1.0 - pulse * 0.55) + error_fill_top.red() * pulse * 0.55)),
                min(255, int(top_color.green() * (1.0 - pulse * 0.55) + error_fill_top.green() * pulse * 0.55)),
                min(255, int(top_color.blue() * (1.0 - pulse * 0.55) + error_fill_top.blue() * pulse * 0.55)),
                top_color.alpha(),
            )
            shadow_color = QColor(
                min(255, int(shadow_color.red() + error_shadow.red() * pulse * 0.25)),
                min(255, int(shadow_color.green() + error_shadow.green() * pulse * 0.25)),
                min(255, int(shadow_color.blue() + error_shadow.blue() * pulse * 0.25)),
                min(255, int(shadow_color.alpha() + error_shadow.alpha())),
            )
        
        for i in range(6):
            x = start_x + (i * (dot_size + spacing))
            y = center_y - (dot_size / 2.0)
            dot_rect = QRectF(float(x), float(y), float(dot_size), float(dot_size))
            render_filled = i < self.pin_count or i == self._shrink_index
            if i == self._pop_index and i < self.pin_count:
                grow = dot_size * (self._pop_scale - 1.0) / 2.0
                dot_rect = dot_rect.adjusted(-grow, -grow, grow, grow)
            elif i == self._shrink_index:
                shrink = dot_size * (1.0 - self._shrink_scale) / 2.0
                dot_rect = dot_rect.adjusted(shrink, shrink, -shrink, -shrink)
            is_filled = render_filled

            shadow_rect = dot_rect.translated(0.0, 1.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(shadow_color if is_filled else QColor(shadow_color.red(), shadow_color.green(), shadow_color.blue(), 24)))
            painter.drawEllipse(shadow_rect)

            if is_filled:
                grad = QLinearGradient(dot_rect.left(), dot_rect.top(), dot_rect.left(), dot_rect.bottom())
                grad.setColorAt(0.0, top_color)
                grad.setColorAt(1.0, bottom_color)
                painter.setBrush(QBrush(grad))
                painter.setPen(QPen(border_color, 0.85))
                painter.drawEllipse(dot_rect)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(highlight_color))
                painter.drawEllipse(dot_rect.adjusted(2.8, 2.0, -2.8, -7.2))
            else:
                empty_fill_top = QColor(255, 255, 255, 18) if not self.charging else QColor(103, 224, 255, 18)
                empty_fill_mid = QColor(25, 34, 47, 38) if not self.charging else QColor(12, 48, 74, 38)
                empty_fill_bottom = QColor(0, 0, 0, 12) if not self.charging else QColor(6, 28, 50, 18)
                empty_fill = QLinearGradient(dot_rect.left(), dot_rect.top(), dot_rect.left(), dot_rect.bottom())
                empty_fill.setColorAt(0.0, empty_fill_top)
                empty_fill.setColorAt(0.48, empty_fill_mid)
                empty_fill.setColorAt(1.0, empty_fill_bottom)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(empty_fill))
                painter.drawEllipse(dot_rect)
                empty_highlight = QColor(255, 255, 255, 18) if not self.charging else QColor(236, 250, 255, 20)
                painter.setBrush(QBrush(empty_highlight))
                painter.drawEllipse(dot_rect.adjusted(3.4, 2.6, -3.4, -8.2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                empty_border.setAlpha(max(64, int(empty_border.alpha() * 0.78)))
                outer_ring = QPen(empty_border, 0.74)
                outer_ring.setCosmetic(True)
                painter.setPen(outer_ring)
                painter.drawEllipse(dot_rect)
                inner_color = QColor(empty_border.red(), empty_border.green(), empty_border.blue(), max(16, empty_border.alpha() // 3))
                inner_ring = QPen(inner_color, 0.36)
                inner_ring.setCosmetic(True)
                painter.setPen(inner_ring)
                painter.drawEllipse(dot_rect.adjusted(2.0, 2.0, -2.0, -2.0))


class PremiumSecurityPinLabel(QWidget):
    """State-aware title label matching the premium lock-screen typography."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = text
        self._charging = False
        self.setMinimumHeight(22)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self.updateGeometry()
        self.update()

    def set_charging(self, charging: bool) -> None:
        self._charging = bool(charging)
        self.update()

    def adjustSize(self) -> None:
        self.resize(self.sizeHint())

    def _font(self):
        from PySide6.QtGui import QFont
        font = QFont("SF Pro Display")
        font.setFamilies(["SF Pro Display", "SF Pro Text", "Segoe UI", "Arial"])
        font.setPointSizeF(12.1)
        font.setWeight(QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.45)
        return font

    def sizeHint(self) -> QSize:
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self._font())
        return QSize(metrics.horizontalAdvance(self._text) + 24, metrics.height() + 12)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        from PySide6.QtGui import QFontMetrics
        font = self._font()
        metrics = QFontMetrics(font)
        x = (self.width() - metrics.horizontalAdvance(self._text)) / 2
        y = (self.height() + metrics.ascent() - metrics.descent()) / 2
        text_path = QPainterPath()
        text_path.addText(QPointF(x, y), font, self._text)
        bounds = text_path.boundingRect()
        if self._charging:
            top_color = QColor(218, 250, 255, 246)
            mid_color = QColor(100, 202, 255, 236)
            bottom_color = QColor(51, 139, 224, 234)
            cast_shadow = QColor(1, 16, 36, 138)
            bevel_shadow = QColor(4, 48, 94, 92)
            bevel_light = QColor(248, 254, 255, 94)
            inner_light = QColor(246, 254, 255, 54)
            edge_color = QColor(122, 222, 255, 54)
            outline_color = QColor(3, 37, 70, 54)
        else:
            top_color = QColor(255, 255, 255, 246)
            mid_color = QColor(238, 244, 250, 236)
            bottom_color = QColor(193, 206, 221, 232)
            cast_shadow = QColor(0, 0, 0, 126)
            bevel_shadow = QColor(54, 65, 82, 82)
            bevel_light = QColor(255, 255, 255, 86)
            inner_light = QColor(255, 255, 255, 48)
            edge_color = QColor(255, 255, 255, 50)
            outline_color = QColor(10, 16, 24, 58)

        painter.setPen(Qt.PenStyle.NoPen)

        from PySide6.QtGui import QPainterPathStroker
        stroker = QPainterPathStroker()
        stroker.setWidth(0.56)
        outline_path = stroker.createStroke(text_path)

        shadow_path = QPainterPath(text_path)
        shadow_path.translate(0.0, 1.15)
        painter.setBrush(QBrush(cast_shadow))
        painter.drawPath(shadow_path)

        bevel_shadow_path = QPainterPath(text_path)
        bevel_shadow_path.translate(0.45, 0.70)
        painter.setBrush(QBrush(bevel_shadow))
        painter.drawPath(bevel_shadow_path)

        bevel_light_path = QPainterPath(text_path)
        bevel_light_path.translate(-0.38, -0.48)
        painter.save()
        painter.setClipRect(QRectF(bounds.left() - 2.0, bounds.top() - 2.0, bounds.width() + 4.0, bounds.height() * 0.62))
        painter.setBrush(QBrush(bevel_light))
        painter.drawPath(bevel_light_path)
        painter.restore()

        painter.setBrush(QBrush(outline_color))
        painter.drawPath(outline_path)

        grad = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.bottom())
        grad.setColorAt(0.0, top_color)
        grad.setColorAt(0.42, mid_color)
        grad.setColorAt(1.0, bottom_color)
        painter.setBrush(QBrush(grad))
        edge_pen = QPen(edge_color, 0.28)
        edge_pen.setCosmetic(True)
        painter.setPen(edge_pen)
        painter.drawPath(text_path)

        highlight_path = QPainterPath(text_path)
        highlight_path.translate(-0.14, -0.24)
        painter.save()
        painter.setClipRect(QRectF(bounds.left() - 1.5, bounds.top() - 1.5, bounds.width() + 3.0, bounds.height() * 0.42))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(inner_light))
        painter.drawPath(highlight_path)
        painter.restore()
        painter.end()

_active_login_dialog = None
def show_login(app: QApplication, parent: Optional[QWidget] = None) -> Optional[User]:
    global _active_login_dialog
    # Tutup dialog login yang masih aktif jika ada
    if _active_login_dialog is not None:
        _active_login_dialog.close()
        _active_login_dialog = None
    dialog = LoginDialog(parent=parent)
    _active_login_dialog = dialog
    dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    # Samakan ukuran dengan AuthenticLockScreen (lock.py)
    width_px = 405
    height_px = int(18.5 * 0.3937 * 96)
    screen = app.primaryScreen()
    screen_geometry = screen.geometry()
    x = screen_geometry.x() + (screen_geometry.width() - width_px) // 2
    y = screen_geometry.y() + (screen_geometry.height() - height_px) // 2
    dialog.setGeometry(x, y, width_px, height_px)
    # ...existing code...
    # Gunakan GLASS_STYLE dari lock.py
    dialog.setStyleSheet(GLASS_STYLE)


    layout = QVBoxLayout()
    layout.setSpacing(0)  # Hilangkan jarak antar widget
    layout.setContentsMargins(0, 0, 0, 0)  # Seragamkan margin atas layout dengan lock.py
    layout.setSpacing(18)

    # --- Position lock.py widgets exactly as in lock.py ---
    # Calculate positions based on lock.py logic
    # Reference: lock.py AuthenticLockScreen __init__
    lock_x = (dialog.width() - 64) // 2  # 64 = lock_icon width
    top_bar_y_offset = 0
    top_bar_visual_bottom = 55 + top_bar_y_offset
    # Battery logo position (kanan atas, menjorok ke atas)
    wifi_logo_width = 20
    wifi_logo_margin_kanan = 4
    battery_logo_margin_kiri = 4
    increased_gap = 20
    wifi_x = lock_x + 64 + 3
    battery_x = wifi_x + wifi_logo_width - wifi_logo_margin_kanan + increased_gap - battery_logo_margin_kiri
    battery_logo = BatteryLogoWidget(dialog)
    battery_logo.setParent(dialog)
    battery_y = top_bar_visual_bottom - battery_logo.height()
    battery_logo.move(battery_x + 5, battery_y)
    battery_logo.show()
    # KeyCapWidget position (sinkron dengan battery_logo)
    keycap = KeyCapWidget(dialog, text="A", battery_widget=battery_logo)
    keycap_x = lock_x - keycap.width() + 3
    keycap_y = top_bar_visual_bottom - keycap.height()
    keycap.move(keycap_x, int(round(keycap_y)))
    keycap.show()
    # Gear widget di kiri keycap, jarak harmonis 20px
    gear_widget = GearIconWidget(dialog)
    gear_widget.set_battery_widget(battery_logo)
    gear_x = keycap_x - gear_widget.width() - 8
    gear_y = int(round(keycap_y + (keycap.height() - gear_widget.height()) / 2))
    gear_widget.move(gear_x, gear_y)
    gear_widget.hide()  # Logo gear dinonaktifkan - dipastikan tersembunyi
    
    # Label jam di sebelah kiri gear widget (custom widget dengan vertical stretch)
    label_clock = VerticalStretchLabel(dialog)
    label_clock.set_charging(False)  # Inisialisasi status charging
    label_clock.setFixedHeight(30)
    
    # Update waktu pada label jam
    from datetime import datetime
    def update_clock_label():
        now = datetime.now()
        time_str = now.strftime("%H.%M")
        # Hanya update jika teks berubah
        if label_clock.text() != time_str:
            label_clock.setText(time_str)
    
    # Update posisi label jam di sebelah kiri keycap (gear disembunyikan)
    def position_clock_label():
        update_clock_label()
        # Hitung lebar teks untuk positioning
        from PySide6.QtGui import QFont, QFontMetrics
        font = QFont('SF Pro Display', -1, QFont.Weight.Thin)
        font.setFamilies(['SF Pro Display', 'SF Pro Text', 'Segoe UI', 'Arial'])
        font.setPointSizeF(17.5)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.35)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(label_clock.text())
        label_clock.setFixedWidth(text_width + 4)
        
        # Jarak label jam ke keycap digeser sedikit ke kiri
        clock_x = keycap_x - label_clock.width() - 3.5
        clock_y = int(round(top_bar_visual_bottom - label_clock.height()))
        label_clock.move(int(clock_x), int(clock_y))
    
    position_clock_label()
    label_clock.show()
    
    # WiFi logo widget di sebelah kanan gembok
    wifi_logo = WiFiLogoWidget(dialog, battery_widget=battery_logo)
    wifi_y = top_bar_visual_bottom - wifi_logo.height()
    wifi_logo.move(int(wifi_x - 4.35), int(round(wifi_y)))
    wifi_logo.show()

    # Jangan tambahkan unlock_icon ke layout, posisikan manual setelah layout di-set

    # Unlock Icon (CustomUnlockIcon/gembok terbuka) - POSISI MANUAL, identik dengan lock.py
    unlock_icon = CustomUnlockIcon(QColor(255, 255, 255))
    unlock_icon.setParent(dialog)
    unlock_icon.set_battery_widget(battery_logo)
    lock_x = (dialog.width() - unlock_icon.width()) // 2  # posisi tengah
    lock_y = int(-4 + 4 + 0.6 + top_bar_y_offset)  # tetap di dalam batas translucent window
    unlock_icon.move(lock_x, lock_y)
    unlock_icon.show()
    dialog.unlock_icon = unlock_icon

    # PIN Entry Grid (iPhone 14 Pro Max style)
    # Label di atas keypad (posisi manual agar jarak visual konsisten)
    label_security_pin = PremiumSecurityPinLabel("Security PIN", dialog)
    label_security_pin.setProperty("charging", "false")

    def apply_security_pin_label_style(charging: bool) -> None:
        label_security_pin.set_charging(charging)

    apply_security_pin_label_style(False)
    
    # Entry PIN (label_pin_entry) langsung di bawah Security Pin
    label_pin_entry = PINDotWidget(dialog)
    MAX_PIN_LENGTH = 6
    MAX_PIN_ATTEMPTS = 5
    LOCKOUT_SECONDS = 30
    _pin_value = ""
    failed_attempts = 0
    pin_locked_out = False

    def set_pin_value(value: str) -> None:
        nonlocal _pin_value
        # Enforce exactly 6 digits max
        _pin_value = value[:MAX_PIN_LENGTH]
        label_pin_entry.set_pin_count(len(_pin_value))

    def append_digit(digit: str) -> None:
        """Tambah digit ke PIN jika belum 6 digit"""
        nonlocal _pin_value, pin_locked_out
        if pin_locked_out:
            return
        if len(_pin_value) < MAX_PIN_LENGTH and digit.isdigit():
            set_pin_value(_pin_value + digit)
            if len(_pin_value) == MAX_PIN_LENGTH:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(120, submit_pin)
    
    def delete_last_digit() -> None:
        """Hapus digit terakhir dari PIN"""
        nonlocal _pin_value, pin_locked_out
        if pin_locked_out:
            return
        if len(_pin_value) > 0:
            set_pin_value(_pin_value[:-1])

    def shake_error() -> None:
        """Animasi getar kiri-kanan pada PIN dot widget sebagai feedback salah."""
        label_pin_entry.trigger_error_pulse()
        orig_x = label_pin_entry.x()
        orig_y = label_pin_entry.y()
        offsets = [8, -8, 6, -6, 4, -4, 0]
        delay = 0
        for offset in offsets:
            def _move(ox: int = orig_x, off: int = offset) -> None:
                label_pin_entry.move(ox + off, orig_y)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(delay, _move)
            delay += 50

    def reset_pin_lockout() -> None:
        """Buka kembali percobaan PIN setelah cooldown selesai."""
        nonlocal failed_attempts, pin_locked_out
        pin_locked_out = False
        failed_attempts = 0
        set_pin_value("")
        QMessageBox.information(
            dialog,
            "PIN Aktif Kembali",
            "Silakan coba lagi. Percobaan PIN direset.",
        )

    def is_pin_charging() -> bool:
        try:
            from ui.battery_status import get_battery_info
        except ImportError:
            from src.ui.battery_status import get_battery_info  # type: ignore

        info = get_battery_info()
        if info:
            charging = info.get("charging")
            if isinstance(charging, bool):
                return charging
            if isinstance(charging, int):
                return bool(charging)
        return bool(getattr(label_pin_entry, "charging", False))

    dialog._pin_charging_provider = is_pin_charging  # type: ignore[attr-defined]

    def submit_pin() -> None:
        """Verifikasi PIN 6 digit. Buka MainForm jika benar, shake+clear jika salah."""
        nonlocal _pin_value, failed_attempts, pin_locked_out
        if pin_locked_out:
            return

        try:
            user = _verify_pin(_pin_value)
        except RuntimeError as error:
            QMessageBox.critical(dialog, "Database Error", str(error))
            set_pin_value("")
            return

        if user is not None:
            dialog.authenticated_user = user
            dialog.accept()
        else:
            failed_attempts += 1
            shake_error()
            from PySide6.QtCore import QTimer
            if failed_attempts >= MAX_PIN_ATTEMPTS:
                pin_locked_out = True
                set_pin_value("")
                QMessageBox.warning(
                    dialog,
                    "PIN Terkunci Sementara",
                    f"Percobaan PIN salah sudah 5 kali. Coba lagi dalam {LOCKOUT_SECONDS} detik.",
                )
                QTimer.singleShot(LOCKOUT_SECONDS * 1000, reset_pin_lockout)
                return

            sisa_coba = MAX_PIN_ATTEMPTS - failed_attempts
            QTimer.singleShot(400, lambda: set_pin_value(""))
            QTimer.singleShot(
                420,
                lambda: _show_credentials_warning(
                    dialog,
                    "Incorrect PIN",
                    f"Incorrect PIN. Attempts remaining: {sisa_coba}.",
                    is_pin_charging(),
                    333,
                    "Security PIN",
                    "pin",
                ),
            )

    set_pin_value("")
    label_security_pin.show()
    label_pin_entry.show()
    
    # Keypad PIN - buat sebelum position_security_label
    pin_grid_container = QWidget(dialog)
    pin_grid = QGridLayout()
    pin_grid.setVerticalSpacing(16)
    pin_grid.setHorizontalSpacing(39)
    pin_grid.setContentsMargins(0, 0, 0, 0)
    pin_labels = ['1', '2', '3',
                 '4', '5', '6',
                 '7', '8', '9',
                 'BACK',  '0', 'BACKSPACE']
    from typing import List, Union
    label_widgets: List[Union[QLabel, RoundLabel, BackspaceButton, BackButton]] = []
    
    def create_keypad_handler(widget: RoundLabel, digit: str):
        """Factory function untuk membuat handler dengan proper closure"""
        original_mouse_press = widget.mousePressEvent
        def handler(event: QMouseEvent) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                append_digit(digit)
            original_mouse_press(event)
        return handler
    
    def create_backspace_handler(widget: BackspaceButton):
        """Factory function untuk membuat backspace handler"""
        original_mouse_press = widget.mousePressEvent
        def handler(event: QMouseEvent) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                delete_last_digit()
            original_mouse_press(event)
        return handler
    
    def create_back_handler(widget: BackButton):
        """Factory function untuk membuat back handler"""
        original_mouse_press = widget.mousePressEvent
        def handler(event: QMouseEvent) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                set_pin_value("")
                dialog.request_back_to_lock = True
                dialog.reject()
            original_mouse_press(event)
        return handler
    
    for i, text in enumerate(pin_labels):
        row = i // 3
        col = i % 3
        if text == 'BACKSPACE':
            # Buat tombol backspace khusus
            lbl = BackspaceButton()
            dialog.keypad_map['backspace'] = lbl
            lbl.mousePressEvent = create_backspace_handler(lbl)
        elif text == 'BACK':
            # Buat tombol back khusus
            lbl = BackButton()
            dialog.keypad_map['back'] = lbl
            lbl.mousePressEvent = create_back_handler(lbl)
        elif text:
            lbl = RoundLabel(text)
            dialog.keypad_map[text] = lbl  # Map angka ke widget
            # Connect click handler untuk append digit
            lbl.mousePressEvent = create_keypad_handler(lbl, text)
        else:
            lbl = QLabel()
            lbl.setFixedSize(56, 56)
            lbl.setStyleSheet('background: transparent; border: none;')
        pin_grid.addWidget(lbl, row, col)
        label_widgets.append(lbl)
    pin_grid_container.setLayout(pin_grid)
    pin_grid_container.adjustSize()
    pin_grid_container.show()
    
    # Define position_security_label function BEFORE calling it
    def position_security_label() -> None:
        label_security_pin.adjustSize()
        security_vertical_offset = 32
        security_pin_top = unlock_icon.y() + unlock_icon.height() + 18 + security_vertical_offset
        security_pin_left = (dialog.width() - label_security_pin.width()) // 2
        label_security_pin.move(security_pin_left, security_pin_top)
        # Target visual: bottom teks ke top lingkaran dot sekitar 22px.
        # PINDotWidget punya padding vertikal internal sekitar 10.4px sebelum dot terlihat.
        pin_entry_top = security_pin_top + label_security_pin.height() + 12
        pin_entry_left = (dialog.width() - label_pin_entry.width()) // 2
        label_pin_entry.move(pin_entry_left, pin_entry_top)
        # Kurangi jarak indikator PIN ke keypad agar lebih rapat
        keypad_top = pin_entry_top + label_pin_entry.height() + 38
        keypad_left = (dialog.width() - pin_grid_container.width()) // 2
        pin_grid_container.move(keypad_left, keypad_top)
    
    position_security_label()

    dialog.setLayout(layout)
    def on_unlock_clicked():
        set_pin_value("")
        dialog.request_back_to_lock = True
        dialog.reject()
    unlock_icon.clicked.connect(on_unlock_clicked)
    # Pastikan unlock_icon selalu di atas
    unlock_icon.raise_()

    # Update charging status periodically with state caching to prevent lag
    from PySide6.QtCore import QTimer
    from typing import Dict, Any, Optional
    from ui.battery_status import get_battery_info
    
    # Cache previous state to avoid unnecessary updates
    _charging_state: Dict[str, Optional[bool]] = {'prev': None}
    
    def update_unlock_icon_charging():
        info: Dict[str, Any] = get_battery_info()  # type: ignore
        charging = bool(info.get('charging', False))
        
        # Only update if state actually changed (prevents lag from redundant updates)
        if _charging_state['prev'] != charging:
            _charging_state['prev'] = charging
            dialog.set_background_charging(charging)
            unlock_icon.set_charging(charging)
            label_pin_entry.set_charging(charging)
            
            # Update keypad button colors
            for widget in label_widgets:
                if isinstance(widget, RoundLabel):
                    widget.set_charging(charging)
                elif isinstance(widget, BackspaceButton):
                    widget.set_charging(charging)
                elif isinstance(widget, BackButton):
                    widget.set_charging(charging)
            
            # Direct stylesheet property update (no unpolish/polish for faster response)
            label_security_pin.setProperty("charging", "true" if charging else "false")
            apply_security_pin_label_style(charging)
            label_security_pin.style().unpolish(label_security_pin)
            label_security_pin.style().polish(label_security_pin)
            
            # Update label jam dengan metode set_charging untuk custom widget
            label_clock.set_charging(charging)
        
        # Update waktu setiap detik
        update_clock_label()
    
    charging_timer = QTimer(dialog)
    charging_timer.timeout.connect(update_unlock_icon_charging)
    charging_timer.start(200)
    update_unlock_icon_charging()  # update awal



    # Reposisi otomatis saat resize
    orig_resize = dialog.resizeEvent if hasattr(dialog, 'resizeEvent') else None
    from PySide6.QtGui import QResizeEvent
    def resizeEvent(event: QResizeEvent) -> None:
        if orig_resize:
            orig_resize(event)
        position_security_label()
    dialog.resizeEvent = resizeEvent
    

    # Tambahkan keyPressEvent untuk menangkap keyboard input

    def keyPressEvent(self: 'LoginDialog', event: QKeyEvent) -> None:
        key_text = event.text()
        # Jika user tekan angka 0-9 di keyboard
        if key_text in self.keypad_map:
            widget: Optional[Union[RoundLabel, BackspaceButton, BackButton]] = self.keypad_map[key_text]
            if widget:
                widget.trigger_press_animation()  # type: ignore[attr-defined]
                append_digit(key_text)
        # Handle Backspace untuk hapus digit
        elif event.key() == Qt.Key.Key_Backspace:
            delete_last_digit()
            if 'backspace' in self.keypad_map:
                backspace_widget: Optional[BackspaceButton] = self.keypad_map['backspace']  # type: ignore
                if backspace_widget:
                    backspace_widget.trigger_press_animation()  # type: ignore[attr-defined]
        # Handle Escape untuk back ke lock.py
        elif event.key() == Qt.Key.Key_Escape:
            self.request_back_to_lock = True
            self.reject()
        QDialog.keyPressEvent(self, event)


    def keyReleaseEvent(self: 'LoginDialog', event: QKeyEvent) -> None:
        key_text = event.text()
        # Jika user lepas angka 0-9 di keyboard
        if key_text in self.keypad_map:
            widget: Optional[Union[RoundLabel, BackspaceButton, BackButton]] = self.keypad_map[key_text]
            if widget:
                widget.trigger_release_animation()  # type: ignore[attr-defined]
        # Handle Backspace release
        elif event.key() == Qt.Key.Key_Backspace:
            if 'backspace' in self.keypad_map:
                backspace_widget: Optional[BackspaceButton] = self.keypad_map['backspace']  # type: ignore
                if backspace_widget:
                    backspace_widget.trigger_release_animation()  # type: ignore[attr-defined]
        # Handle Escape release untuk back
        elif event.key() == Qt.Key.Key_Escape:
            if 'back' in self.keypad_map:
                back_widget: Optional[BackButton] = self.keypad_map['back']  # type: ignore
                if back_widget:
                    back_widget.trigger_release_animation()  # type: ignore[attr-defined]
        QDialog.keyReleaseEvent(self, event)

    dialog.keyPressEvent = keyPressEvent.__get__(dialog)
    dialog.keyReleaseEvent = keyReleaseEvent.__get__(dialog)
    
    dialog.exec()
    _active_login_dialog = None

    if dialog.request_back_to_lock:
        if show_lock():
            return show_login(app, parent)
        return None

    if dialog.authenticated_user is not None:
        return dialog.authenticated_user
    return None
