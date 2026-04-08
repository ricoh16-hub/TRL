from importlib import import_module
from typing import Callable, Optional, Union, cast
from database.models import User
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QGridLayout, QLabel, QGraphicsDropShadowEffect, QToolTip, QApplication, QMessageBox
from PySide6.QtCore import Qt, Signal, QRectF, QEasingCurve, QPropertyAnimation, Property, QEvent, QPointF
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QRadialGradient, QMouseEvent, QPaintEvent, QEnterEvent, QKeyEvent, QCloseEvent
from PySide6.QtCore import QRect
from PySide6.QtGui import QLinearGradient
# Import widgets from lock.py
from ui.lock import BatteryLogoWidget, KeyCapWidget, GearIconWidget, WiFiLogoWidget, show_lock

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
        self._animate_scale(self._scale, 0.85, 100)
    
    def trigger_release_animation(self) -> None:
        """Public method to trigger release animation from outside"""
        self._animate_scale(self._scale, 1.0, 150)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 0.85, 100)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 1.0, 150)
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Backspace):
            self._animate_scale(self._scale, 0.85, 100)
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
        
        # Triple layer dengan lingkaran penuh untuk setiap layer
        layers: list[dict[str, float]] = [
            {'radius': 28.0, 'scale': 1.0, 'opacity_base': 35.0, 'opacity_max': 160.0},
            {'radius': 27.3, 'scale': 0.9, 'opacity_base': 55.0, 'opacity_max': 200.0},
            {'radius': 26.5, 'scale': 0.75, 'opacity_base': 30.0, 'opacity_max': 140.0}
        ]
        
        # Gambar base circles untuk semua layer terlebih dahulu
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in layers:
            radius: float = layer['radius']
            opacity_base: float = layer['opacity_base']
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity_base)), 0.6, Qt.PenStyle.SolidLine))
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
                    
                    if thickness > 0.02 and opacity > 15:
                        border_color = QColor(255, 255, 255, opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, thickness, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
                else:
                    # Area di luar ridge tetap ada subtle outline
                    subtle_opacity = int(opacity_base * 0.4)
                    if subtle_opacity > 10:
                        border_color = QColor(255, 255, 255, subtle_opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, 0.3, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
        
        # Tentukan warna berdasarkan status charging
        if self.charging:
            icon_color = QColor(80, 180, 255)
        else:
            icon_color = QColor(255, 255, 255)
        
        # Gambar custom backspace icon: trapezoid + X mark
        # Ukuran dan posisi trapezoid - centered di lingkaran (28, 28)
        trap_width = 20.0  # lebar bagian kanan trapezoid
        trap_height = 14.0
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
        arrow_x = trap_center_x - trap_width / 2 - 5.5
        arrow_y = trap_center_y
        
        # Gambar trapezoid outline
        line_thickness = 1.0
        painter.setPen(QPen(icon_color, line_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
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
        x_size = 5.5
        x_center_x = 28.0 + 1.0  # Center lingkaran + offset visual balance (sama dengan trapezoid)
        x_center_y = 28.0  # Center lingkaran
        x_thickness = 1.0
        
        painter.setPen(QPen(icon_color, x_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
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
        self._animate_scale(self._scale, 0.85, 100)
    
    def trigger_release_animation(self) -> None:
        """Public method to trigger release animation from outside"""
        self._animate_scale(self._scale, 1.0, 150)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 0.85, 100)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(self._scale, 1.0, 150)
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Escape):
            self._animate_scale(self._scale, 0.85, 100)
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
        
        # Triple layer dengan lingkaran penuh untuk setiap layer
        layers: list[dict[str, float]] = [
            {'radius': 28.0, 'scale': 1.0, 'opacity_base': 35.0, 'opacity_max': 160.0},
            {'radius': 27.3, 'scale': 0.9, 'opacity_base': 55.0, 'opacity_max': 200.0},
            {'radius': 26.5, 'scale': 0.75, 'opacity_base': 30.0, 'opacity_max': 140.0}
        ]
        
        # Gambar base circles untuk semua layer terlebih dahulu
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in layers:
            radius: float = layer['radius']
            opacity_base: float = layer['opacity_base']
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity_base)), 0.6, Qt.PenStyle.SolidLine))
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
                    
                    if thickness > 0.02 and opacity > 15:
                        border_color = QColor(255, 255, 255, opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, thickness, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
                else:
                    # Area di luar ridge tetap ada subtle outline
                    subtle_opacity = int(opacity_base * 0.4)
                    if subtle_opacity > 10:
                        border_color = QColor(255, 255, 255, subtle_opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, 0.3, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
        
        # Tentukan warna berdasarkan status charging: biru saat charging, putih saat normal
        if self.charging:
            outline = QColor(80, 180, 255)
            fill = QColor(80, 180, 255)
        else:
            outline = QColor(255, 255, 255)
            fill = QColor(255, 255, 255)
        
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
        
        pen_width = 1.0
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
        painter.setPen(QPen(outline, 0.55, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
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
        painter.setPen(QPen(fill, 0.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
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
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._text = ""
        self._charging = False
        self._scale = 1.0  # Scale proporsional (X dan Y)
        self._vertical_scale = 1.0  # Tetap untuk kompatibilitas
        self._scale_anim = None
        self.setMinimumHeight(18)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
        self._animate_scale(self._scale, 1.15, 180)
        # Efek glow biru terang saat hover
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffect(shadow)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_scale(self._scale, 1.0, 180)
        self.setGraphicsEffect(None)  # type: ignore[arg-type]
        super().leaveEvent(event)
        
    def setText(self, text: str):
        self._text = text
        self.update()
    
    def text(self) -> str:
        """Get current text"""
        return self._text
        
    def set_charging(self, charging: bool):
        self._charging = charging
        self.update()
        
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        # Warna teks berdasarkan charging status
        if self._charging:
            text_color = QColor(80, 180, 255)  # Blue
        else:
            text_color = QColor(255, 255, 255)  # White
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
        painter.setPen(text_color)
        # Hitung dimensi teks normal
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        # Hitung dimensi teks normal
        from PySide6.QtGui import QFontMetrics
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
        # Gambar teks di posisi center
        rect = QRectF(-text_width/2, -text_height/2, text_width, text_height)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)
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
                font-family: 'SF Pro Display';
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
        self._animate_scale(self._scale, 0.85, 100)
    
    def trigger_release_animation(self) -> None:
        """Public method to trigger release animation from outside"""
        self._animate_scale(self._scale, 1.0, 150)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Tenggelam ke 0.85
            self._animate_scale(self._scale, 0.85, 100)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Timbul kembali ke 1.0
            self._animate_scale(self._scale, 1.0, 150)
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            # Tenggelam ke 0.85
            self._animate_scale(self._scale, 0.85, 100)
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
        
        # Triple layer dengan lingkaran penuh untuk setiap layer
        layers: list[dict[str, float]] = [
            {'radius': 28.0, 'scale': 1.0, 'opacity_base': 35.0, 'opacity_max': 160.0},
            {'radius': 27.3, 'scale': 0.9, 'opacity_base': 55.0, 'opacity_max': 200.0},
            {'radius': 26.5, 'scale': 0.75, 'opacity_base': 30.0, 'opacity_max': 140.0}
        ]
        
        # Gambar base circles untuk semua layer terlebih dahulu
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for layer in layers:
            radius: float = layer['radius']
            opacity_base: float = layer['opacity_base']
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            painter.setPen(QPen(QColor(255, 255, 255, int(opacity_base)), 0.6, Qt.PenStyle.SolidLine))
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
                    
                    if thickness > 0.02 and opacity > 15:
                        border_color = QColor(255, 255, 255, opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, thickness, Qt.PenStyle.SolidLine))
                        painter.drawArc(rect, int(angle_qt * 16), 16)
                else:
                    # Area di luar ridge tetap ada subtle outline
                    subtle_opacity = int(opacity_base * 0.4)
                    if subtle_opacity > 10:
                        border_color = QColor(255, 255, 255, subtle_opacity)
                        angle_qt = current_angle - 90.0
                        painter.setPen(QPen(border_color, 0.3, Qt.PenStyle.SolidLine))
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
            text_color = QColor(80, 180, 255)
        else:
            text_color = QColor(255, 255, 255)
        
        # Gambar angka
        number_font = QFont()
        number_font.setFamilies(['SF Pro Display', 'SF Pro Text'])
        number_font.setPointSize(18)
        # Medium weight: tidak bold, tidak normal
        painter.setFont(number_font)
        painter.setPen(text_color)
        
        number_rect = self.rect().adjusted(0, number_offset, 0, number_offset)
        painter.drawText(number_rect, Qt.AlignmentFlag.AlignCenter, self.number_text)
        
        # Gambar alfabet di bawah (jika ada)
        if self.number_text in self.alphabet_map:
            alphabet_text = self.alphabet_map[self.number_text]
            alphabet_font = QFont()
            alphabet_font.setFamilies(['SF Pro Display', 'SF Pro Text'])
            alphabet_font.setPointSize(5)
            alphabet_font.setBold(True)
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
        margin_x = 8
        padlock_w = W - 2 * margin_x
        # Dynamic gradient for body fill
        body_width = 21.5
        body_height = 18
        body_x = int(margin_x + (padlock_w - body_width) // 2)
        body_y = int(36.75)
        painter.setPen(Qt.PenStyle.NoPen)
        # Gradient for unlock body
        body_rect = QRect(int(body_x), int(body_y), int(body_width), int(body_height))
        if self.charging:
            # Gradasi biru aqua premium ke electric blue lembut dari kiri ke kanan
            gradient = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.right(), body_rect.bottom())
            gradient.setColorAt(0.0, QColor(78, 217, 255))   # #4ED9FF
            gradient.setColorAt(1.0, QColor(90, 167, 255))  # #5AA7FF
            painter.setBrush(QBrush(gradient))
        else:
            # Gunakan self.lock_color sebagai warna utama body
            base_color = self.lock_color if hasattr(self, 'lock_color') else QColor(255, 255, 255)
            gradient = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.bottom())
            gradient.setColorAt(0.0, base_color)
            gradient.setColorAt(1.0, QColor(230, 230, 230))
            painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(body_rect, 3.1, 3.1)
        # SHACKLE (open)
        shackle_width = 11
        shackle_height = 13.5
        shackle_x = int(body_x + (body_width - shackle_width) // 2)
        shackle_y = body_y - 7.5
        painter.setBrush(Qt.BrushStyle.NoBrush)
        shackle_rect = QRect(int(shackle_x), int(shackle_y), int(shackle_width), int(shackle_height))
        # Shackle: gunakan warna sesuai charging atau self.lock_color
        if self.charging:
            shackle_pen = QPen(QColor(78, 217, 255, 240), 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        else:
            shackle_color = self.lock_color if hasattr(self, 'lock_color') else QColor(255, 255, 255, 240)
            shackle_pen = QPen(shackle_color, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        painter.setPen(shackle_pen)
        # Draw open shackle (arc, not full circle)
        painter.drawArc(shackle_rect, 30 * 16, 210 * 16)  # arc dari kiri ke atas, kanan terbuka
        # (Dihapus) Garis kaki kiri shackle ke body agar visual lebih bersih
        # KEYHOLE
        keyhole_x = int(W // 2)
        keyhole_y = int(body_y + body_height // 2)
        painter.setPen(QPen(QColor(15, 20, 30, 200), 1))
        painter.setBrush(QBrush(QColor(15, 20, 30, 200)))
        painter.drawEllipse(int(keyhole_x - 2), int(keyhole_y - 2), 4, 4)
        painter.drawRect(int(keyhole_x - 1), int(keyhole_y + 1), 2, 3)
        painter.setPen(QPen(QColor(34, 42, 54, 255), 1))
        painter.setBrush(QBrush(QColor(34, 42, 54, 255)))
        painter.drawEllipse(int(keyhole_x - 1), int(keyhole_y - 1), 2, 2)
        painter.drawRect(int(keyhole_x - 1), int(keyhole_y), 2, 2)
        highlight_alpha = 120
        painter.setPen(QPen(QColor(75, 85, 100, highlight_alpha), 1))
        painter.setBrush(QBrush(QColor(75, 85, 100, highlight_alpha)))
        painter.drawPoint(int(keyhole_x), int(keyhole_y))
        # FINISHING TOUCHES
        highlight_color = QColor(255, 255, 255, 100)
        painter.setPen(QPen(highlight_color, 0.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(int(body_x + 1), int(body_y + 1), int(body_x + body_width - 1), int(body_y + 1))
        painter.drawLine(int(body_x + 1), int(body_y + 1), int(body_x + 1), int(body_y + body_height - 1))
        # (Dihapus) Arc highlight finishing touches pada shackle agar tidak terjadi duplikasi lengkungan
        # (Dihapus) Glow lingkaran biru saat hover agar identik dengan CustomLockIcon

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
        self._shackle_anim = None
        self._shackle_angle = 180  # degrees, open
        self._on_shackle_closed = None
        self._shackle_open = True
        self.charging = charging
        self._hovering = False

    def set_charging(self, charging: bool):
        self.charging = charging
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
        self._scale_anim.setEndValue(1.18)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        # Efek glow biru terang saat hover
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffect(shadow)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self._hovering = False
        self.update()
        self.animate_to_normal()
        self.unsetCursor()
        self.setGraphicsEffect(None)  # type: ignore
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
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.18))
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()

GLASS_STYLE = """
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #222a36, stop:1 #3a4a5c);
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,0.18);
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
        QToolTip.showText(self.mapToGlobal(self.rect().center()), self.toolTip())

    def leaveEvent(self, event: QEvent):
        self.hovered = False
        self.update()

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
        self.setToolTip("Kembali ke Home")
        self._hover = False
    def enterEvent(self, event: QEnterEvent) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)
    def leaveEvent(self, event: QEvent) -> None:
        self._hover = False
        self.update()
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

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.unlock_icon: Optional[CustomUnlockIcon] = None
        self.authenticated_user: Optional[User] = None
        self.request_back_to_lock: bool = False
        self.security_pin_logged: bool = False
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        # Hilangkan efek transparan dan animasi opacity agar background solid
        self.keypad_map: dict[str, Optional[Union[RoundLabel, BackspaceButton, BackButton]]] = {}  # Map angka/backspace/back ke widget

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)

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
        self.setFixedSize(200, 55)
        self.pin_count = 0
        self.is_complete = False
        self.charging = False
        
    def set_pin_count(self, count: int) -> None:
        """Update number of filled dots (0-6)"""
        self.pin_count = min(count, 6)
        self.is_complete = (self.pin_count == 6)
        self.update()
        
    def set_charging(self, charging: bool) -> None:
        """Update charging status and trigger repaint"""
        self.charging = charging
        self.update()
        
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw 6 circular dots (50% smaller)
        dot_size = 14  # was 28
        spacing = 14   # was 6
        total_width = (dot_size * 6) + (spacing * 5)
        start_x = (self.width() - total_width) // 2
        center_y = self.height() // 2
        
        # Colors - filled_color bergantung pada charging status
        if self.charging:
            filled_color = QColor(90, 167, 255)   # Biru lembut #5AA7FF saat charging
        else:
            filled_color = QColor(255, 255, 255)  # Putih #FFFFFF saat tidak charging
        
        empty_color = QColor(0, 0, 0, 0)          # Transparan
        
        # Draw each circular dot
        for i in range(6):
            x = start_x + (i * (dot_size + spacing))
            y = center_y - (dot_size // 2)
            
            # Determine if this dot should be filled
            is_filled = i < self.pin_count
            dot_color = filled_color if is_filled else empty_color
            
            # Draw circular dot (ellipse) WITH WHITE BORDER
            # Border color berdasarkan charging status
            if self.charging:
                border_color = QColor(90, 167, 255)  # Biru lembut #5AA7FF
            else:
                border_color = QColor(255, 255, 255)  # Putih #FFFFFF
            border_width = 0.95
            painter.setPen(QPen(border_color, border_width, Qt.PenStyle.SolidLine))
            painter.setBrush(dot_color)
            painter.drawEllipse(int(x), int(y), dot_size, dot_size)

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
    # Battery logo position (kanan atas, menjorok ke atas)
    wifi_logo_width = 20
    wifi_logo_margin_kanan = 4
    battery_logo_margin_kiri = 4
    increased_gap = 20
    wifi_x = lock_x + 64 + 3
    battery_x = wifi_x + wifi_logo_width - wifi_logo_margin_kanan + increased_gap - battery_logo_margin_kiri
    battery_y = 27
    battery_logo = BatteryLogoWidget(dialog)
    battery_logo.setParent(dialog)
    battery_logo.move(battery_x + 5, battery_y)
    battery_logo.show()
    # KeyCapWidget position (sinkron dengan battery_logo)
    keycap = KeyCapWidget(dialog, text="A", battery_widget=battery_logo)
    keycap_x = lock_x - keycap.width() + 3
    keycap_y = 25 - 10 + 5 + 3 + 0.5
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
        font.setPointSizeF(17.5)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.35)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(label_clock.text())
        label_clock.setFixedWidth(text_width + 4)
        
        # Jarak label jam ke keycap digeser sedikit ke kiri
        clock_x = keycap_x - label_clock.width() - 3.5
        # Turunkan sedikit agar lebih dekat dengan garis horizontal atas
        clock_y = int(round(keycap_y + (keycap.height() - label_clock.height()) / 2)) + 1.8
        label_clock.move(int(clock_x), int(clock_y))
    
    position_clock_label()
    label_clock.show()
    
    # WiFi logo widget di sebelah kanan gembok
    wifi_logo = WiFiLogoWidget(dialog, battery_widget=battery_logo)
    y_garis = 36.75 + 18 + 2
    wifi_logo_height = 20
    wifi_y = y_garis - wifi_logo_height - 3 - 2 + 0.25
    wifi_y += 1
    wifi_logo.move(int(wifi_x - 4.35), int(round(wifi_y - 1.45 - 8 + 3 + 3 + 0.25 + 0.25 + 0.35 + 0.5 - 3)))
    wifi_logo.show()

    # Jangan tambahkan unlock_icon ke layout, posisikan manual setelah layout di-set

    # Unlock Icon (CustomUnlockIcon/gembok terbuka) - POSISI MANUAL, identik dengan lock.py
    unlock_icon = CustomUnlockIcon(QColor(255, 255, 255))
    unlock_icon.setParent(dialog)
    lock_x = (dialog.width() - unlock_icon.width()) // 2  # posisi tengah
    lock_y = int(-10 + 4 + 0.6)  # Samakan dengan lock.py
    unlock_icon.move(lock_x, lock_y)
    unlock_icon.show()
    dialog.unlock_icon = unlock_icon

    # PIN Entry Grid (iPhone 14 Pro Max style)
    # Label di atas keypad (posisi manual agar jarak visual konsisten)
    label_security_pin = QLabel("Security Pin", dialog)
    label_security_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label_security_pin.setStyleSheet(QSS_LABEL_STYLE + "font-family: 'SF Pro Display', 'SF Pro Text'; font-size: 12px; font-weight: 855; letter-spacing: 0.5px;")
    label_security_pin.setProperty("charging", "false")
    
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
                lambda: QMessageBox.warning(
                    dialog,
                    "PIN Salah",
                    f"PIN salah. Sisa percobaan: {sisa_coba}.",
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
        security_vertical_offset = 36
        security_pin_top = unlock_icon.y() + unlock_icon.height() + 18 + security_vertical_offset
        security_pin_left = (dialog.width() - label_security_pin.width()) // 2
        label_security_pin.move(security_pin_left, security_pin_top)
        # Tambah jarak label Security Pin ke dot PIN
        pin_entry_top = security_pin_top + label_security_pin.height() + 8
        pin_entry_left = (dialog.width() - label_pin_entry.width()) // 2
        label_pin_entry.move(pin_entry_left, pin_entry_top)
        # Kurangi jarak indikator PIN ke keypad agar lebih rapat
        keypad_top = pin_entry_top + label_pin_entry.height() + 28
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
            label_security_pin.style().polish(label_security_pin)  # Only polish, not unpolish
            
            # Update label jam dengan metode set_charging untuk custom widget
            label_clock.set_charging(charging)
        
        # Update waktu setiap detik
        update_clock_label()
    
    charging_timer = QTimer(dialog)
    charging_timer.timeout.connect(update_unlock_icon_charging)
    charging_timer.start(1000)  # update setiap 1000 ms (1 detik) - lebih efisien
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
    def keyPressEvent(event: QKeyEvent) -> None:
        key_text = event.text()
        # Jika user tekan angka 0-9 di keyboard
        if key_text in dialog.keypad_map:
            widget = dialog.keypad_map[key_text]
            if widget:
                # Trigger animasi tenggelam
                widget.trigger_press_animation()
                # Append digit ke PIN
                append_digit(key_text)
        # Handle Backspace untuk hapus digit
        elif event.key() == Qt.Key.Key_Backspace:
            delete_last_digit()
            # Trigger animasi backspace button
            if 'backspace' in dialog.keypad_map:
                backspace_widget = dialog.keypad_map['backspace']
                if backspace_widget:
                    backspace_widget.trigger_press_animation()
        # Handle Escape untuk back ke lock.py
        elif event.key() == Qt.Key.Key_Escape:
            dialog.request_back_to_lock = True
            dialog.reject()
        QDialog.keyPressEvent(dialog, event)
    
    def keyReleaseEvent(event: QKeyEvent) -> None:
        key_text = event.text()
        # Jika user lepas angka 0-9 di keyboard
        if key_text in dialog.keypad_map:
            widget = dialog.keypad_map[key_text]
            if widget:
                # Trigger animasi timbul
                widget.trigger_release_animation()
        # Handle Backspace release
        elif event.key() == Qt.Key.Key_Backspace:
            # Trigger animasi backspace button
            if 'backspace' in dialog.keypad_map:
                backspace_widget = dialog.keypad_map['backspace']
                if backspace_widget:
                    backspace_widget.trigger_release_animation()
        # Handle Escape release untuk back
        elif event.key() == Qt.Key.Key_Escape:
            if 'back' in dialog.keypad_map:
                back_widget = dialog.keypad_map['back']
                if back_widget:
                    back_widget.trigger_release_animation()
        QDialog.keyReleaseEvent(dialog, event)
    
    dialog.keyPressEvent = keyPressEvent
    dialog.keyReleaseEvent = keyReleaseEvent
    
    dialog.exec()
    _active_login_dialog = None

    if dialog.request_back_to_lock:
        if show_lock():
            return show_login(app, parent)
        return None

    if dialog.authenticated_user is not None:
        return dialog.authenticated_user
    return None
