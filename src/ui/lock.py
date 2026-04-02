from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from PySide6.QtCore import QEvent, QPointF, QPropertyAnimation, QRect, Qt, QTimer, Signal, QEasingCurve, Property
from PySide6.QtGui import QBrush, QCloseEvent, QColor, QEnterEvent, QFont, QKeyEvent, QLinearGradient, QMouseEvent, QPaintEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QWidget


def get_theme_color(charging: bool) -> str:
    """Return hex color string for charging or not charging state."""
    return "#50B4FF" if charging else "#FFFFFF"


@runtime_checkable
class BatteryWidgetProtocol(Protocol):
    charging: bool

GLASS_STYLE = """
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #222a36, stop:1 #3a4a5c);
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,0.18);
    }
"""

QSS_LABEL_STYLE = """
QLabel[charging="true"] {
    color: #50B4FF;
}
QLabel[charging="false"] {
    color: #FFFFFF;
}
"""

def show_lock() -> bool:
    """Show authentic Lock Screen dialog and return True if accepted."""
    lock_dialog = AuthenticLockScreen()
    lock_dialog.setModal(True)
    result = lock_dialog.exec()
    return result == QDialog.DialogCode.Accepted

# --- WiFiLogoWidget (restored from backup/src/ui/lock.py) ---
class WiFiLogoWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, battery_widget: Optional[QWidget] = None):
        self.battery_widget: Optional[QWidget] = battery_widget
        self._wifi_name = "Tidak diketahui"  # Inisialisasi lebih awal agar selalu ada
        super().__init__(parent)
        if self.battery_widget and hasattr(self.battery_widget, 'timer'):
            self.battery_widget.timer.timeout.connect(self.update)  # type: ignore[attr-defined]
        # Default/base size, will be animated
        self._base_size = 28  # Perbesar ukuran widget Wi-Fi sekitar 30%
        self.setFixedSize(int(self._base_size), int(self._base_size))
        self._scale = 1.0
        self._scale_anim = None  # Ensure _scale_anim can be None
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Enable transparent background so drawing can overflow widget bounds
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._wifi_timer = QTimer(self)
        self._wifi_timer.timeout.connect(self.update_wifi_status)
        self._wifi_timer.start(500)  # refresh setiap 0.5 detik (ideal: responsif & efisien)

    def update_wifi_status(self):
        try:
            import subprocess
            result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True)
            # Simpan output ke file untuk analisis
            try:
                with open('wifi_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
            except Exception:
                pass
            lines = result.stdout.splitlines()
            ssid = None
            for line in lines:
                line = line.strip()
                # Cari baris SSID (dengan spasi) dan value tidak kosong, sesuai output netsh user
                if line.startswith('SSID') and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Pastikan key persis 'SSID' (bukan 'BSSID', dll) dan value tidak kosong
                    if key == 'SSID' and value:
                        ssid = value
                        break
            if ssid:
                self._wifi_name = ssid
            else:
                self._wifi_name = "Not Connected"
        except Exception:
            self._wifi_name = "Unknown"
        self.update()  # Paksa repaint agar warna langsung berganti

    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        # Jangan ubah ukuran widget, biarkan tetap agar posisi dot konsisten
        self.update()

    scale = Property(float, get_scale, set_scale)

    def _animate_scale(self, start: float, end: float):
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        # Batalkan animasi lama jika masih berjalan
        if hasattr(self, '_scale_anim') and self._scale_anim is not None:
            self._scale_anim.stop()
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda _: self.update())  # type: ignore
        anim.finished.connect(lambda: setattr(self, '_scale_anim', None))
        anim.start()
        self._scale_anim = anim

    def enterEvent(self, event: QEnterEvent):
        self._animate_scale(getattr(self, '_scale', 1.0), 1.18)  # 1.18 sama seperti CustomLockIcon
        # Efek glow biru terang saat hover
        from PySide6.QtWidgets import QGraphicsDropShadowEffect, QToolTip
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffect(shadow)
        # Ambil nama WiFi dari fungsi get_Wifi_info
        self.setToolTip(f"Wi-Fi : {self._wifi_name}")
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.toolTip(), self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self._animate_scale(getattr(self, '_scale', 1.18), 1.0)
        # Kembalikan efek bayangan normal (atau hilangkan efek)
        self.setGraphicsEffect(None)  # type: ignore
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        scale = getattr(self, '_scale', 1.0)
        painter.translate(W / 2 + 0.875, H / 2)
        painter.scale(scale, scale)
        painter.translate(-W / 2, -H / 2)
        margin = 4
        icon_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        icon_W, icon_H = icon_rect.width(), icon_rect.height()
        center_x = icon_rect.left() + icon_W / 2
        vertical_offset = 1
        base_y = icon_rect.top() + icon_H * 0.62 + vertical_offset
        arc_thickness = 1.0
        # Tentukan warna berdasarkan status WiFi dan charging
        status = self._wifi_name.strip().lower()
        charging = False
        if self.battery_widget and hasattr(self.battery_widget, 'charging'):
            charging = getattr(self.battery_widget, 'charging', False)  # type: ignore[attr-defined]
        if status not in ("unknown", "not connected") and charging:
            # Connected and charging: blue
            arc_color = QColor(80, 180, 255, 255)
            dot_color = QColor(80, 180, 255, 255)
        else:
            # Not connected or not charging: white
            arc_color = QColor(255, 255, 255, 255)
            dot_color = QColor(255, 255, 255, 255)
        arc_span = 125
        arc_radii = [icon_W * 0.22]  # lengkungan kecil
        arc_gap = 3
        arc_radii.append(arc_radii[0] + arc_gap)      # lengkungan sedang
        arc_radii.append(arc_radii[1] + arc_gap)      # lengkungan besar
        arc_radii.append(arc_radii[2] + arc_gap)      # lengkungan paling besar (tambahan)
        for radius in arc_radii:
            painter.setPen(QPen(arc_color, arc_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(
                int(center_x - radius), int(base_y - radius),
                int(2 * radius), int(2 * radius),
                (90 - arc_span // 2) * 16, arc_span * 16
            )
        dot_radius = 1.5
        arc_bottom_y = base_y + arc_radii[0]
        dot_y = arc_bottom_y
        painter.setBrush(dot_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(center_x - dot_radius), int(dot_y - dot_radius), int(2 * dot_radius), int(2 * dot_radius))

# Battery logo widget
class BatteryLogoWidget(QWidget):
    """Widget to display a battery logo with glassmorphism style"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(int(36.5), 26)
        self.battery_level: float = 1.0
        self.battery_percent: int = 100
        self.charging: bool = False
        self._scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Timer untuk update status baterai
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_battery_status)
        self.timer.start(10)  # update setiap 0.01 detik
    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    # Properti scale saja, tanpa rotasi
    from PySide6.QtCore import Property
    scale = Property(float, get_scale, set_scale)

    def update_battery_status(self):
        try:
            from .battery_status import get_battery_info as _get_battery_info
            info: Optional[dict[str, object]] = _get_battery_info()  # type: ignore
            if info is not None:
                percent = info.get('percent', 100)
                self.battery_percent = int(percent) if isinstance(percent, (int, float, str)) else 100
                self.battery_level = self.battery_percent / 100.0
                charging = info.get('charging', False)
                self.charging = bool(charging) if isinstance(charging, (bool, int)) else False
            else:
                self.battery_percent = 100
                self.battery_level = 1.0
                self.charging = False
        except Exception:
            self.battery_percent = 100
            self.battery_level = 1.0
            self.charging = False
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # Geser semua gambar ke bawah 0.45 px
        painter.translate(self.width() / 2, self.height() / 2 + 0.45)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        # Harmonize margin: use fixed margin (4 px) like WiFiLogoWidget and KeyCapWidget
        margin = 4
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        body_x = rect.left()
        body_y = rect.top()
        body_width = rect.width()
        body_height = rect.height()
        body_rect = QRect(body_x, body_y, body_width, body_height)
        # Outline & tip color logic
        # Outline color: biru saat charging, putih saat tidak
        if self.charging:
            outline_color = QColor(80, 180, 255)  # #50B4FF
        else:
            outline_color = QColor(255, 255, 255, 255)  # putih
        # Outline
        painter.setPen(QPen(outline_color, 0.45))
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawRoundedRect(body_rect, 2.5, 2.5)
        # Tip: persegi kecil, solid, tanpa border
        tip_w = 1.5
        tip_h = 6  # Tinggi kepala battery diubah menjadi 6 piksel
        gap_px = 2
        tip_x = body_x + body_width + gap_px
        tip_y = body_y + (body_height - tip_h) // 2
        tip_rect = QRect(int(tip_x), int(tip_y), int(tip_w), int(tip_h))
        tip_pen = QPen(outline_color, 0.45)
        tip_pen.setStyle(Qt.PenStyle.SolidLine)
        tip_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(tip_pen)
        painter.setBrush(QColor(0, 0, 0, 0))  # tanpa fill
        painter.drawRect(tip_rect)
        # Battery fill: solid, flat
        fill_margin = 3
        fill_height = 10  # Tinggi isi baterai tetap 10 piksel
        fill_width = int((int(body_width) - 2 * int(fill_margin)) * float(self.battery_level))
        # Posisikan fill_rect agar vertikalnya benar-benar di tengah body
        fill_y = body_y + (body_height - fill_height) // 2
        fill_rect = QRect(body_x + fill_margin, fill_y, fill_width, fill_height)
        if self.charging:
            # Gradasi biru aqua premium ke electric blue lembut dari kiri ke kanan
            gradient = QLinearGradient(fill_rect.left(), fill_rect.top(), fill_rect.right(), fill_rect.bottom())
            gradient.setColorAt(0.0, QColor(78, 217, 255))   # #4ED9FF (aqua premium)
            gradient.setColorAt(1.0, QColor(90, 167, 255))  # #5AA7FF (electric blue lembut)
            painter.setBrush(QBrush(gradient))
            painter.drawRect(fill_rect)
        else:
            # Gradasi putih ke abu-abu muda dari atas ke bawah
            gradient = QLinearGradient(fill_rect.left(), fill_rect.top(), fill_rect.left(), fill_rect.bottom())
            gradient.setColorAt(0.0, QColor(255, 255, 255))
            gradient.setColorAt(1.0, QColor(230, 230, 230))
            painter.setBrush(QBrush(gradient))
            painter.drawRect(fill_rect)
        # Inner shadow ala Figma
        shadow_rect = fill_rect.adjusted(1, 1, -1, -1)
        shadow_gradient = QLinearGradient(shadow_rect.left(), shadow_rect.top(), shadow_rect.left(), shadow_rect.bottom())
        shadow_gradient.setColorAt(0, QColor(0, 0, 0, 40))
        shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 2, 2)

        # Tambahkan simbol petir saat charging
        if self.charging:
            # Simbol petir presisi (berdasarkan SVG Material Design)
            # Path: M11 15H6l7-14v8h5l-7 14z
            # Skala dan pusatkan ke fill_rect
            svg_w = 24
            scale = min(fill_rect.width(), fill_rect.height()) / svg_w * 1.25
            offset_x = fill_rect.center().x() - (12 * scale)
            offset_y = fill_rect.center().y() - (12 * scale)
            points = [
                QPointF(11, 15),
                QPointF(6, 15),
                QPointF(13, 1),
                QPointF(13, 9),
                QPointF(18, 9),
                QPointF(11, 23),
            ]
            # Transform ke posisi dan skala yang sesuai
            points = [QPointF(p.x() * scale + offset_x, p.y() * scale + offset_y) for p in points]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawPolygon(points)
        # No restore needed; no save was called
    def enterEvent(self, event: QEnterEvent) -> None:
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.0))
        self._scale_anim.setEndValue(1.18)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        # Efek glow biru terang saat hover
        from PySide6.QtWidgets import QGraphicsDropShadowEffect, QToolTip
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffect(shadow)
        # Tooltip dinamis
        self.setToolTip(f"Status : {self.battery_percent}%")
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.toolTip(), self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        try:
            self._scale_anim = QPropertyAnimation(self, b"scale")
            self._scale_anim.setStartValue(getattr(self, '_scale', 1.18))
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.setDuration(220)
            self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._scale_anim.valueChanged.connect(self.update)
            self._scale_anim.start()
            # Kembalikan efek bayangan normal (atau hilangkan efek)
            self.setGraphicsEffect(None)  # type: ignore
            super().leaveEvent(event)
        except KeyboardInterrupt:
            pass
    # Properti scale saja, tanpa rotasi
    # get_scale and set_scale already defined above
    # from PySide6.QtCore import Property
    # scale = Property(float, get_scale, set_scale)
    scale = Property(float, get_scale, set_scale)

class CustomLockIcon(QWidget):
    def enterEvent(self, event: QEnterEvent):
        self._hovering = True
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
    """Custom lock icon widget with iPhone-quality animations"""
    clicked = Signal()

    def __init__(self, color: QColor = QColor(255, 255, 255), parent: Optional[QWidget] = None, charging: bool = False):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Login")
        self.lock_color: QColor = color
        self.original_color: QColor = color
        self.charging: bool = charging
        self._hovering: bool = False
        self.battery_widget = None  # type: ignore
        self._charging_timer = None  # type: ignore
        self.setFixedSize(64, 64)
        # Find BatteryLogoWidget in parent hierarchy or children
        p = self.parent()
        while p is not None:
            try:
                from .lock import BatteryLogoWidget
                if isinstance(p, BatteryLogoWidget):
                    self.battery_widget = p
                    break
                children = []
                if hasattr(p, 'children') and callable(getattr(p, 'children')):
                    children = list(getattr(p, 'children')())
                for child in children:
                    if isinstance(child, BatteryLogoWidget):
                        self.battery_widget = child
                        break
                if self.battery_widget:
                    break
            except Exception:
                pass
            p = getattr(p, 'parent', lambda: None)()
        # Timer polling charging status
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._update_charging_status)
        self._charging_timer.start(200)

    def _update_charging_status(self) -> None:
        charging = False
        if self.battery_widget is not None:
            charging = getattr(self.battery_widget, 'charging', False)
        if charging != self.charging:
            self.charging = charging
            self.update()

    def leaveEvent(self, event: QEvent):
        self._hovering = False
        self.update()
        self.animate_to_normal()
        self.unsetCursor()
        # Kembalikan efek bayangan normal (atau hilangkan efek)
        self.setGraphicsEffect(None)  # type: ignore
        super().leaveEvent(event)
    # Duplikasi paintEvent dihapus, hanya satu paintEvent yang digunakan

    def mousePressEvent(self, event: 'QMouseEvent'):
        # Semua tombol mouse trigger klik
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self.animate_to_normal()
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: 'QMouseEvent'):
        # Double click juga trigger
        self.animate_to_normal()
        self.clicked.emit()
        super().mouseDoubleClickEvent(event)

    def animate_to_normal(self):
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.311))
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()

    def get_scale(self):
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float):
        self._scale = value
        self.update()

    scale = Property(float, get_scale, set_scale)

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
        # Gradient for lock body
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
        # SHACKLE
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
        painter.drawArc(shackle_rect, 0, 180 * 16)
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
        painter.drawArc(int(shackle_x + 1), int(shackle_y + 1), int(shackle_width - 2), int(shackle_height - 2), 10 * 16, 160 * 16)
        # No restore needed; no save was called

    def setColor(self, color: QColor) -> None:
        self.lock_color = color
        self.update()

class ChevronExitButton(QWidget):
    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    scale = Property(float, get_scale, set_scale)

    def get_collapse_progress(self) -> float:
        return getattr(self, '_collapse_progress', 0.0)

    def set_collapse_progress(self, value: float) -> None:
        self._collapse_progress = value
        self.update()

    collapse_progress = Property(float, get_collapse_progress, set_collapse_progress)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(48, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Exit")
        self._hover = False
        self._scale = 1.0
        self._scale_anim = None
        self._collapsed = False  # Status collapse chevron
        self._collapse_progress = 0.0
        self._collapse_anim = None
        self._charging = False
        # Cari BatteryLogoWidget di parent (AuthenticLockScreen)
        self._battery_widget = None
        p = self.parent()
        from PySide6.QtWidgets import QWidget
        while p is not None:
            from .lock import BatteryLogoWidget
            if isinstance(p, BatteryLogoWidget):
                self._battery_widget = p
                break
            # Cek children parent, jika ada BatteryLogoWidget
            children: list[QWidget] = []
            if hasattr(p, 'children') and callable(getattr(p, 'children')):
                children = list(getattr(p, 'children')())
            for child in children:
                if isinstance(child, BatteryLogoWidget):
                    self._battery_widget = child
                    break
            if self._battery_widget:
                break
            p = getattr(p, 'parent', lambda: None)()
        # Timer polling charging status
        from PySide6.QtCore import QTimer
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._update_charging_status)
        self._charging_timer.start(200)

    def _update_charging_status(self) -> None:
        charging = False
        if self._battery_widget is not None:
            charging = getattr(self._battery_widget, 'charging', False)
        if charging != self._charging:
            self._charging = charging
            self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hover = True
        # Efek glow biru terang saat hover
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffect(shadow)
        # Animasi skala seperti logo gembok
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.0))
        self._scale_anim.setEndValue(1.28)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hover = False
        # Kembalikan efek bayangan normal (abu-abu transparan)
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(80, 80, 80, 120))
        self.setGraphicsEffect(shadow)
        # Animasi skala kembali ke normal
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.28))
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._collapsed = not self._collapsed
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            self._collapse_anim = QPropertyAnimation(self, b"collapse_progress")
            self._collapse_anim.setStartValue(self._collapse_progress)
            self._collapse_anim.setEndValue(1.0 if self._collapsed else 0.0)
            self._collapse_anim.setDuration(220)
            self._collapse_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._collapse_anim.valueChanged.connect(self.update)
            if self._collapsed:
                # Setelah animasi selesai, tutup form aktif lalu keluar aplikasi
                def on_finished():
                    win = self.window()
                    if win:
                        win.close()
                    from PySide6.QtWidgets import QApplication
                    QApplication.quit()
                self._collapse_anim.finished.connect(on_finished)
            self._collapse_anim.start()
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.translate(w/2, h/2)
        painter.scale(getattr(self, '_scale', 1.0), getattr(self, '_scale', 1.0))
        painter.translate(-w/2, -h/2)
        # Jarak antar ujung kiri dan kanan chevron: 32.9px
        chevron_width = 32.9
        chevron_height = 12.0  # tinggi chevron (bisa disesuaikan agar sudut bawah proporsional)
        center_x = w / 2
        center_y = h / 2
        x1 = center_x - chevron_width / 2
        x3 = center_x + chevron_width / 2
        y1 = center_y - chevron_height / 2
        y3 = y1
        # Titik bawah (ujung bawah chevron)
        y2 = center_y + chevron_height / 2
        x2 = center_x
        # Collapse progress (animasi ke garis lurus)
        p = getattr(self, '_collapse_progress', 0.0)
        yh = center_y
        y1a = (1-p)*y1 + p*yh
        y2a = (1-p)*y2 + p*yh
        y3a = (1-p)*y3 + p*yh
        # Warna gradasi mengikuti status charging
        if self._charging:
            grad = QLinearGradient(x1, y1a, x3, y3a)
            grad.setColorAt(0.0, QColor(78, 217, 255))
            grad.setColorAt(1.0, QColor(90, 167, 255))
        else:
            grad = QLinearGradient(x1, y1a, x3, y3a)
            grad.setColorAt(0.0, QColor(255, 255, 255))
            grad.setColorAt(1.0, QColor(230, 230, 230))
        pen = QPen(QBrush(grad), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(x1), int(y1a), int(x2), int(y2a))
        painter.drawLine(int(x2), int(y2a), int(x3), int(y3a))

class TimeVerticalStretchLabel(QWidget):
    """Label dengan teks yang di-stretch vertikal untuk jam besar dengan horizontal compression seperti iPhone"""
    def __init__(self, parent: Optional[QWidget] = None, font_size: float = 160.0,
                 font_weight: QFont.Weight = QFont.Weight.Thin, letter_spacing: float = 0.0,
                 vertical_scale: float = 1.0, horizontal_scale: float = 0.75):
        super().__init__(parent)
        self._text = ""
        self._charging = False
        self._font_size = font_size
        # Always store font_weight as QFont.Weight
        self._font_weight = QFont.Weight(font_weight)
        self._letter_spacing = letter_spacing
        self._vertical_scale = vertical_scale
        self._horizontal_scale = horizontal_scale
        self.setMinimumHeight(200)
        self.setMinimumWidth(180)
        
    def setText(self, text: str):
        self._text = text
        self.updateGeometry()  # Update size hint ketika text berubah
        self.update()
    
    def text(self) -> str:
        """Get current text"""
        return self._text
        
    def set_charging(self, charging: bool):
        self._charging = charging
        self.update()
    
    def sizeHint(self):
        from PySide6.QtGui import QFont, QFontMetrics
        from PySide6.QtCore import QSize
        font = QFont()
        # Gunakan font monospace yang sangat ramping dan tinggi, fallback jika tidak tersedia
        font.setFamily('IBM Plex Mono')
        if not QFontMetrics(font).inFont('0'):
            font.setFamily('Fira Mono')
        font.setWeight(QFont.Weight.ExtraLight if hasattr(QFont.Weight, 'ExtraLight') else QFont.Weight.Thin)
        font.setPointSizeF(self._font_size)
        font.setStretch(QFont.Stretch.Condensed)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, self._letter_spacing)
        metrics = QFontMetrics(font)
        text_width = int(metrics.horizontalAdvance(self._text if self._text else "00") * self._horizontal_scale)
        text_height = int(metrics.height() * self._vertical_scale)
        return QSize(text_width + 32, text_height + 32)
        
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self._charging:
            text_color = QColor(80, 180, 255)
        else:
            text_color = QColor(255, 255, 255)
        from PySide6.QtGui import QFont, QFontMetrics, QPainterPath
        font = QFont()
        font.setFamily('IBM Plex Mono')
        if not QFontMetrics(font).inFont('0'):
            font.setFamily('Fira Mono')
        font.setWeight(QFont.Weight.ExtraLight if hasattr(QFont.Weight, 'ExtraLight') else QFont.Weight.Thin)
        font.setPointSizeF(self._font_size)
        font.setStretch(QFont.Stretch.Condensed)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, self._letter_spacing)
        metrics = QFontMetrics(font)
        text_height = metrics.height()
        painter.save()
        center_x = self.width() / 2
        center_y = self.height() / 2
        painter.translate(center_x, center_y)
        painter.scale(self._horizontal_scale, self._vertical_scale)
        from PySide6.QtCore import QPointF
        thin_color = QColor(text_color)
        thin_color.setAlpha(240)
        total_width: float = 0.0
        char_widths: list[int] = []
        for char in self._text:
            char_width: int = metrics.horizontalAdvance(char)
            char_widths.append(char_width)
            total_width += char_width
        if len(self._text) > 1:
            total_width += self._letter_spacing * (len(self._text) - 1)
        x_pos: float = -total_width / 2
        y_pos: float = float(text_height / 2 - metrics.descent())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(thin_color))
        for i, char in enumerate(self._text):
            path = QPainterPath()
            path.addText(QPointF(x_pos, y_pos), font, char)
            painter.drawPath(path)
            x_pos += char_widths[i] + self._letter_spacing
        painter.restore()

class AuthenticLockScreen(QDialog):
    def update_time_label_styles(self):
        charging = False
        if hasattr(self, 'battery_logo') and self.battery_logo:
            charging = getattr(self.battery_logo, 'charging', False)
        
        # Update custom widget labels dengan method set_charging
        self.hour_label.set_charging(charging)
        self.minute_label.set_charging(charging)
        
        # Update QLabel reguler dengan property
        value = "true" if charging else "false"
        for label in [self.dot_label, self.date_label]:
            label.setProperty("charging", value)
            label.style().unpolish(label)
            label.style().polish(label)


    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

    def cleanup(self) -> None:
        """Stop timers and clean up resources."""
        try:
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure timer is stopped on close for clean exit."""
        self.cleanup()
        super().closeEvent(event)
    """
    ULTRA-PREMIUM iPhone-style Lock Screen dengan LUXURY VISUALIZATION
    
    ✅ COMPLETE LUXURY FEATURES:
    - 69% MEGA scale animations dengan 8° rotation dan dual-layer glow
    - LUXURY DATE/TIME VISUALIZATION dengan gradient colors serasi boot.py
    - Premium QGraphicsDropShadowEffect dengan mu
    lti-layer glow
    - Enhanced typography (font-weight 500 date, 100 time, letter-spacing)
    - MAXIMUM PROXIMITY positioning (total -18px elevation)
    - TEXT CLIPPING FIX dengan enhanced padding dan line-height
    - Layout reordering: Lock → Date → Time (sesuai request)
    - San Francisco typography consistency di semua elemen
    - Balanced lock positioning (10px margins) untuk perfect visual harmony
    - Zero gaps antar elemen untuk ultimate compactness
    
    LATEST ENHANCEMENT: Luxury visualization dengan efek mewah serasi boot.py
    """
    def __init__(self) -> None:
        super().__init__()
        # Setup window FIRST
        from PySide6.QtGui import QColor
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # Increase width only, keep height unchanged
        self.setFixedSize(405, int(18.5 * 0.3937 * 96))
        self.setStyleSheet(GLASS_STYLE)
        # Tempatkan window di tengah layar seperti boot.py
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)

        # --- Lock/Unlock icon logic ---
        from .login import CustomUnlockIcon
        self.lock_icon = CustomLockIcon(QColor(255, 255, 255), parent=self)
        self.unlock_icon = CustomUnlockIcon(QColor(255, 255, 255), parent=self)
        self.lock_x = (self.width() - self.lock_icon.width()) // 2
        lock_y = -10
        self.lock_icon.setParent(self)
        self.lock_icon.move(self.lock_x, int(lock_y + 4 + 0.6))
        self.lock_icon.show()
        # Place unlock icon at same position, but hidden by default
        self.unlock_icon.setParent(self)
        self.unlock_icon.move(self.lock_x, int(lock_y + 4 + 0.6))
        self.unlock_icon.hide()

        # --- Dynamic color update for lock icon ---
        if hasattr(self, 'battery_logo') and self.battery_logo:
            self.battery_logo.timer.timeout.connect(self._update_lock_icon_color)
            self.battery_logo.timer.timeout.connect(self.update_time_label_styles)
        self._update_lock_icon_color()

        # --- Periodic charging update for unlock icon with state caching ---
        from ui.battery_status import get_battery_info
        from typing import Optional, Dict, Any
        
        # Cache previous state to avoid unnecessary updates (prevents lag)
        self._lock_charging_state: Optional[bool] = None
        
        def update_unlock_icon_charging():
            info: Optional[Dict[str, Any]] = get_battery_info()
            if info is not None:
                charging = bool(info.get('charging', False))
                # Only update if state changed (avoids redundant rendering)
                if self._lock_charging_state != charging:
                    self._lock_charging_state = charging
                    self.unlock_icon.set_charging(charging)
        
        self.unlock_charging_timer = QTimer(self)
        self.unlock_charging_timer.timeout.connect(update_unlock_icon_charging)
        self.unlock_charging_timer.start(200)
        update_unlock_icon_charging()

    def _update_lock_icon_color(self):
        """Update lock icon color to match battery/chevron logic."""
        from PySide6.QtGui import QColor
        if hasattr(self, 'battery_logo') and self.battery_logo:
            charging = getattr(self.battery_logo, 'charging', False)
            if charging:
                # When charging, the lock icon uses blue gradient in paintEvent, so set color to white (not used)
                self.lock_icon.setColor(QColor(255, 255, 255))
            else:
                # When not charging, use off-white/gray (same as chevron logic)
                self.lock_icon.setColor(QColor(255, 255, 255))  # You can adjust to QColor(230,230,230) for more gray
        # Battery logo di kanan atas, sedikit menjorok ke atas
        self.battery_logo = BatteryLogoWidget(self)
        # --- Explicitly set battery widget reference in lock icon for charging sync ---
        self.lock_icon.battery_widget = self.battery_logo
        # Geser battery agar tepi kiri battery tepat 3 px dari tepi kanan WiFi
        wifi_x = self.lock_x + self.lock_icon.width() + 3
        wifi_logo_width = 20  # default WiFiLogoWidget width
        wifi_logo_margin_kanan = 4
        battery_logo_margin_kiri = 4
        increased_gap = 20
        battery_x = wifi_x + wifi_logo_width - wifi_logo_margin_kanan + increased_gap - battery_logo_margin_kiri

        # KeyCapWidget sinkron dengan battery_logo
        self.keycap = KeyCapWidget(self, text="A", battery_widget=self.battery_logo)
        keycap_x = self.lock_x - self.keycap.width() + 3
        keycap_y = 25 - 10 + 5 + 3 + 0.5
        self.keycap.move(keycap_x, int(round(keycap_y)))
        self.keycap.show()
        # Gear widget di kiri keycap, jarak harmonis 20px
        self.gear_widget = GearIconWidget(self)
        self.gear_widget.set_battery_widget(self.battery_logo)
        gear_x = keycap_x - self.gear_widget.width() - 8
        gear_y = int(round(keycap_y + (self.keycap.height() - self.gear_widget.height()) / 2))
        self.gear_widget.move(gear_x, gear_y)
        self.gear_widget.show()

        # Declare missing attributes for lint compliance
        self.time_label: QLabel = QLabel(self)
        self.unlock_text: QLabel = QLabel(self)
        # Restore battery logo to visible top position
        # Calculate battery logo position just above red line
        # Use garis1_y from paintEvent and battery_logo.height() for placement
        battery_y = 27  # Naikkan 2px agar sedikit lebih tinggi
        self.battery_logo.setParent(self)
        self.battery_logo.move(battery_x + 5, battery_y)  # geser kanan 2px lagi
        self.battery_logo.show()

        # WiFi logo widget baru di sebelah kanan gembok, jarak 30px
        wifi_x = self.lock_x + self.lock_icon.width() + 3
        # Position WiFi logo so its bottom is 3 px above the red line
        y_garis = 36.75 + 18 + 2
        wifi_logo_height = 20  # px - ukuran lebih besar
        # Turunkan logo WiFi sekitar 0.25 px (gunakan float, lalu dibulatkan saat move)
        wifi_y = y_garis - wifi_logo_height - 3 - 2 + 0.25  # Sudah ada offset 0.25, tambahkan lagi 0.25
        wifi_y += 1  # Turunkan 1 pixel penuh agar pasti terlihat
        self.wifi_logo = WiFiLogoWidget(self, battery_widget=self.battery_logo)
        # Geser posisi widget logo WiFi 0.5 px ke kiri dan turunkan lagi 0.5px
        self.wifi_logo.move(int(wifi_x - 4.35), int(round(wifi_y - 1.45 - 8 + 3 + 3 + 0.25 + 0.25 + 0.35 + 0.5 - 3)))  # geser kiri 1px lagi
        self.wifi_logo.show()

        # Hitung dan print jarak dari bawah widget logo WiFi ke garis merah
        # Connect padlock click to show login
        self.lock_icon.clicked.connect(self.show_login_form)
        # Create date label
        self.date_label = QLabel(self)
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet("""
QLabel {
    color: rgb(255,255,255);
    font-family: 'SF Pro Display';
    font-size: 12px;
    font-weight: 350;
    letter-spacing: 0.5px;
}
""")
        self.time_container = QWidget(self)
        self.time_layout = QHBoxLayout(self.time_container)
        self.time_layout.setContentsMargins(0, 0, 0, 0)
        self.time_layout.setSpacing(0)
        
        # Gunakan TimeVerticalStretchLabel untuk jam dan menit dengan vertical stretch + horizontal compression
        from PySide6.QtGui import QFont
        self.hour_label = TimeVerticalStretchLabel(
            parent=self,
            font_size=110.47,
            font_weight=QFont.Weight.ExtraLight,
            letter_spacing=15.0,
            vertical_scale=3.13,
            horizontal_scale=0.62
        )
        self.minute_label = TimeVerticalStretchLabel(
            parent=self,
            font_size=110.47,
            font_weight=QFont.Weight.ExtraLight,
            letter_spacing=15.0,
            vertical_scale=3.13,
            horizontal_scale=0.62
        )
        
        # SOLUSI Z-ORDER: Buat label jam transparan untuk mouse events
        # Clock tetap visible tapi tidak menghalangi click pada widget lain
        self.hour_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.minute_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.dot_label = QLabel()
        # Style jam dan menit dengan warna off-white dan shadow
        # Style jam digital besar (jam, titik, menit) di bawah tanggal
        # hour_label dan minute_label sudah diatur oleh TimeVerticalStretchLabel
        self.dot_label.setStyleSheet(QSS_LABEL_STYLE + "font-family: 'SF Pro Display', 'Segoe UI', 'Arial', sans-serif; font-size: 20px; font-weight: 100; background: rgba(0,0,0,0); padding: 0px;")
        self.dot_label.setFixedSize(20, 20)
        self.dot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # SOLUSI Z-ORDER: Dot label juga transparan untuk mouse events
        self.dot_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.date_label.setStyleSheet(QSS_LABEL_STYLE + "font-family: 'SF Pro Display', 'SF Pro Text'; font-size: 12px; font-weight: 655; letter-spacing: 0.5px;")
    # (rollback: hapus pewarnaan dinamis label jam)

        # Efek shadow pada label dot dan date (hour dan minute sudah diatur oleh widget custom)
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        for label in [self.dot_label]:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(16)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 3)
            label.setGraphicsEffect(shadow)
        
        # Set alignment untuk semua label
        self.dot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_label.setContentsMargins(0, 0, 0, 0)
        self.dot_label.setContentsMargins(-5, 0, -5, 0)
        self.minute_label.setContentsMargins(0, 0, 0, 0)
        self.time_layout.addWidget(self.hour_label)
        self.time_layout.addWidget(self.dot_label)
        self.time_layout.addWidget(self.minute_label)
        # Atur margin atas pada dot_label agar titik turun ke tengah angka
        self.time_layout.setStretch(0, 1)
        self.time_layout.setStretch(1, 0)
        self.time_layout.setStretch(2, 1)
        # margin atas 0px agar titik benar-benar di tengah (sudah diatur di atas)
        self.time_container.setLayout(self.time_layout)
        
        # SOLUSI Z-ORDER: Time container juga transparan untuk mouse events
        self.time_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # Update time and date
        self.update_time_date()
        self.date_label.adjustSize()
        self.time_container.adjustSize()
        # Pastikan posisi label langsung benar sejak awal
        self.reposition_labels()
        self.date_label.show()
        self.time_container.show()
        # Hilangkan efek glow agar bounding box label minimal
        self.setup_timer()
        
        # SOLUSI Z-ORDER: Naikkan semua widget interaktif ke depan (di atas clock)
        # Ini memastikan mereka tetap clickable dan animasi berfungsi
        self.lock_icon.raise_()
        self.unlock_icon.raise_()
        self.battery_logo.raise_()
        self.wifi_logo.raise_()
        self.keycap.raise_()
        self.gear_widget.raise_()
        self.date_label.raise_()  # Date juga bisa diklik jika perlu

        # Tambahkan ChevronExitButton di tengah bawah, tepat di bawah garis horizontal bawah
        self.chevron_exit = ChevronExitButton(self)
        # Hitung posisi y_garis_bawah dari paintEvent
        y_garis_bawah = self.height() - 56.75
        chevron_x = (self.width() - self.chevron_exit.width()) // 2
        chevron_y = int(y_garis_bawah + 0)  # 0px di bawah garis horizontal bawah (menempel)
        self.chevron_exit.move(chevron_x, chevron_y)
        self.chevron_exit.show()
        
        # SOLUSI Z-ORDER: Chevron exit juga harus di depan
        self.chevron_exit.raise_()
    def show_login_form(self):
        try:
            self.hide()  # Sembunyikan form lock.py sebelum menampilkan LoginDialog
            from .login import show_login
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            show_login_func = show_login
            if isinstance(app, QApplication):
                # Kirim self sebagai parent agar LoginDialog bisa menyesuaikan ukuran LockForm
                if isinstance(self, LockForm):
                    show_login_func(app, self)
                else:
                    show_login_func(app, None)
            else:
                print("[ERROR] QApplication instance not found.")
                return
        except Exception as e:
            import traceback
            print("[ERROR] show_login_form exception:", e)
            traceback.print_exc()
        
    def apply_luxury_effects(self):
        # Apply premium graphics effects yang serasi dengan boot.py
        # Premium glow effect untuk date label
        date_glow = QGraphicsDropShadowEffect()
        date_glow.setBlurRadius(20)
        date_glow.setColor(QColor(255, 255, 255, 80))
        date_glow.setOffset(0, 1)
        self.date_label.setGraphicsEffect(date_glow)
        
        # Premium glow effect untuk time label dengan depth yang lebih besar
        time_glow = QGraphicsDropShadowEffect()
        time_glow.setBlurRadius(32)
        time_glow.setColor(QColor(255, 255, 255, 100))
        time_glow.setOffset(0, 3)
        self.time_label.setGraphicsEffect(time_glow)
        
    def setup_interactions(self) -> None:
        # Setup authentic iPhone interactions
        # Semua event mouse (klik kiri/kanan) pada logo gembok telah dihapus.
        # Tidak ada mousePressEvent, mouseReleaseEvent, atau event handler lain.
        # Logo gembok hanya tampil statis tanpa aksi interaktif.
        
        # Keyboard shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def setup_timer(self) -> None:
        # Setup timer to update time every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_date)
        self.timer.start(1000)  # Update every second
        
    def update_time_date(self) -> None:
        # Update time and date display
        try:
            now = self.get_current_datetime()
            time_str = self.format_time(now)
            date_str = self.format_date(now)
            self.update_time_label(time_str)
            self.update_date_label(date_str)
            self.reposition_labels()
            self.update_time_label_styles()
        except KeyboardInterrupt:
            self.cleanup()
            print("[INFO] Proses dihentikan manual. Timer dan resource dibersihkan.")

    def get_current_datetime(self) -> datetime:
        # Get current datetime object (for testability)
        return datetime.now()

    def format_time(self, dt: datetime) -> str:
        # Format time as HH.MM (24-hour)
        return dt.strftime("%H.%M")

    def format_date(self, dt: datetime) -> str:
        # Format date as 'Wkd, DD Mon YYYY' (3 karakter, bahasa sesuai locale)
        import locale
        try:
            locale.setlocale(locale.LC_TIME, '')  # Ikuti settingan sistem
        except Exception:
            pass  # fallback jika gagal
        weekday = dt.strftime("%a")  # 3 karakter hari, sesuai locale
        month = dt.strftime("%b")    # 3 karakter bulan, sesuai locale
        day = dt.strftime("%d")
        year = dt.strftime("%Y")
        return f"{weekday}, {day} {month} {year}"

    def update_time_label(self, time_str: str) -> None:
        # Pisahkan jam, titik, dan menit
        if '.' in time_str:
            jam, menit = time_str.split('.')
            self.hour_label.setText(jam)
            self.dot_label.setText('■')
            self.minute_label.setText(menit)
        else:
            self.hour_label.setText(time_str)
            self.dot_label.setText('')
            self.minute_label.setText('')
        self.time_container.adjustSize()

    def update_date_label(self, date_str: str) -> None:
        self.date_label.setText(date_str)
        self.date_label.adjustSize()

    def reposition_labels(self) -> None:
        gap_below_gembok = 18  # Turunkan label tanggal 10px lebih jauh dari gembok
        gap_below_date = -136  # Kurangi sedikit lagi jarak agar lebih rapat
        vertical_offset_down = 34  # Turunkan blok tanggal + jam ke bawah
        time_offset_down = 28  # Turunkan jam besar ke bawah
        # Posisi label tanggal tepat di bawah gembok
        date_y = self.lock_icon.y() + self.lock_icon.height() + gap_below_gembok + vertical_offset_down
        # Pusatkan label tanggal secara horizontal
        date_x = (self.width() - self.date_label.width()) // 2
        self.date_label.move(date_x, date_y)
        time_y = date_y + self.date_label.height() + gap_below_date + time_offset_down
        self.time_container.adjustSize()  # Pastikan ukuran jam sudah sesuai layout baru
        time_x = (self.width() - self.time_container.width()) // 2
        self.time_container.move(time_x, time_y)
        
    def unlock_animation(self) -> None:
        # Animate unlock with iPhone-style smooth transitions
        # Trigger the lock icon's unlock sequence
        # Removed call to animate_unlock_sequence as it does not exist in CustomLockIcon
        pass
        
        # Create smooth text and interface animations
        text_fade = QPropertyAnimation(self.unlock_text, b"windowOpacity")
        text_fade.setDuration(300)
        text_fade.setStartValue(0.8)
        text_fade.setEndValue(1.0)
        text_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Update unlock text with fade
        self.unlock_text.setText("Unlocking...")
        self.unlock_text.setStyleSheet(
            "QLabel {"
            "color: #4CD564;"
            "font-family: 'SF Pro Display';"
            "font-weight: 500;"
            "background: transparent;"
            "}"
        )
        
        text_fade.start()
        
        # Create elegant dialog fade out animation
        dialog_fade = QPropertyAnimation(self, b"windowOpacity")
        dialog_fade.setDuration(600)
        dialog_fade.setStartValue(1.0)
        dialog_fade.setEndValue(0.0)
        dialog_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Delay the dialog fade to let the unlock animation play
        QTimer.singleShot(800, lambda: dialog_fade.start())
        
        # Close dialog after complete animation
        QTimer.singleShot(1400, self.accept)
        
    def keyPressEvent(self, event: 'QKeyEvent') -> None:
        # Handle keyboard events
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space]:
            self.unlock_animation()
        else:
            super().keyPressEvent(event)
            

# LockForm definition after AuthenticLockScreen
class LockForm(AuthenticLockScreen):
    def __init__(self):
        super().__init__()
        # ...existing code...

class KeyCapWidget(QWidget):
    def _animate_scale(self, start: float, end: float) -> None:
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        if getattr(self, '_scale_anim', None):
            self._scale_anim.stop()
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(lambda: setattr(self, '_scale_anim', None))
        anim.start()
        self._scale_anim = anim

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate_scale(getattr(self, '_scale', 1.0), 1.15)
        # Efek glow biru terang saat hover
        from PySide6.QtWidgets import QGraphicsDropShadowEffect, QToolTip
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffect(shadow)
        # Tooltip dinamis: tampilkan status CapsLock dan Shift
        caps_status = "On" if self._capslock_on else "Off"
        shift_status = "On" if self._shift_on else "Off"
        tooltip_text = f"CapsLock : {caps_status}\nShift : {shift_status}"
        self.setToolTip(tooltip_text)
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.toolTip(), self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_scale(getattr(self, '_scale', 1.15), 1.0)
        # Kembalikan efek bayangan normal (atau hilangkan efek)
        self.setGraphicsEffect(None)  # type: ignore
        super().leaveEvent(event)

    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    from PySide6.QtCore import Property
    scale = Property(float, get_scale, set_scale)

    def __init__(self, parent: Optional[QWidget] = None, text: str = "A", battery_widget: Optional[BatteryWidgetProtocol] = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text = text
        self.setFixedSize(int(36.5), 29)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._capslock_on = False
        self._shift_on = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_keyboard_state)
        self._timer.start(200)
        self._poll_keyboard_state()
        self.charging = False
        self._battery_widget: Optional[BatteryWidgetProtocol] = battery_widget
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._sync_charging_status)
        self._charging_timer.start(200)

    def set_battery_widget(self, battery_widget: Optional[BatteryWidgetProtocol]) -> None:
        self._battery_widget = battery_widget
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._sync_charging_status)
        self._charging_timer.start(200)

    def _sync_charging_status(self) -> None:
        if isinstance(self._battery_widget, BatteryWidgetProtocol):
            charging = getattr(self._battery_widget, 'charging', False)
            if getattr(self, 'charging', False) != charging:
                self.charging = charging
                self.update()

    def _poll_keyboard_state(self):
        # Windows-specific: use win32api to check key state
        try:
            import ctypes
            VK_CAPITAL = 0x14
            VK_SHIFT = 0x10
            user32 = ctypes.windll.user32
            capslock = user32.GetKeyState(VK_CAPITAL) & 0x0001
            shift = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
            changed = (self._capslock_on != bool(capslock)) or (self._shift_on != bool(shift))
            self._capslock_on = bool(capslock)
            self._shift_on = bool(shift)
            if changed:
                self.update()
                # Update tooltip realtime
                caps_status = "On" if self._capslock_on else "Off"
                shift_status = "On" if self._shift_on else "Off"
                tooltip_text = f"CapsLock : {caps_status}\nShift : {shift_status}"
                self.setToolTip(tooltip_text)
                from PySide6.QtWidgets import QToolTip
                QToolTip.hideText()
                QToolTip.showText(self.mapToGlobal(self.rect().center()), tooltip_text, self)
        except Exception:
            pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = getattr(self, '_scale', 1.0)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(scale, scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        rect = self.rect().adjusted(4, int(7.5), -4, int(-4.5))
        radius = 2.5

        # --- LOGIKA WARNA BARU ---
        charging = getattr(self, 'charging', False)
        # Outline keycap
        if charging:
            outline_color = QColor(90, 167, 255)  # blue lembut
        else:
            outline_color = QColor(255, 255, 255, 255)  # putih
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outline_color, 0.45))
        painter.drawRoundedRect(rect, radius, radius)

        # LED indikator CapsLock
        led_diameter = 2.8
        led_x = rect.left() + 3
        led_y = rect.top() + 3
        if charging:
            if self._capslock_on:
                led_color = QColor(255, 255, 255, 255)  # putih terang
            else:
                led_color = QColor(90, 167, 255)  # blue lembut
        else:
            if self._capslock_on:
                led_color = QColor(80, 180, 255)  # biru terang
            else:
                led_color = QColor(255, 255, 255, 255)  # putih
        painter.setBrush(QBrush(led_color))
        painter.setPen(QPen(led_color, 1))
        painter.drawEllipse(int(led_x), int(led_y), int(2 * led_diameter), int(2 * led_diameter))

        # Simbol panah (Shift)
        arrow_height = 6
        center_x = rect.center().x() + 2
        center_y = rect.center().y() + 3 - 0.75
        shaft_top = center_y - arrow_height // 2 + 2
        shaft_bottom = center_y + arrow_height // 2
        shaft_width = 2
        if charging:
            if self._shift_on:
                shaft_color = QColor(255, 255, 255, 255)  # putih terang
            else:
                shaft_color = QColor(90, 167, 255)  # blue lembut
        else:
            if self._shift_on:
                shaft_color = QColor(80, 180, 255)  # biru terang
            else:
                shaft_color = QColor(255, 255, 255, 255)  # putih
        painter.setPen(QPen(shaft_color, 0.8))
        painter.setBrush(shaft_color)
        painter.drawRect(int(center_x - shaft_width//2), int(shaft_top), int(shaft_width), int(shaft_bottom - shaft_top))

        # Arrowhead
        head_height = 4
        head_width = 8
        head_top = shaft_top - head_height
        left_base = center_x - head_width//2
        right_base = center_x + head_width//2
        base_y = shaft_top
        from PySide6.QtGui import QPainterPath
        arrowhead = QPainterPath()
        arrowhead.moveTo(center_x, head_top)
        arrowhead.lineTo(left_base, base_y)
        arrowhead.lineTo(right_base, base_y)
        arrowhead.closeSubpath()
        painter.setBrush(QBrush(shaft_color))
        painter.setPen(QPen(shaft_color, 0.8))
        painter.drawPath(arrowhead)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outline_color, 0.45))
        painter.end()

class GearIconWidget(QWidget):
    gearHovered = Signal()
    gearUnhovered = Signal()
    _battery_widget: Optional[QWidget] = None

    def set_battery_widget(self, battery_widget: Optional[QWidget]) -> None:
        self._battery_widget = battery_widget
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._sync_charging_status)
        self._charging_timer.start(200)

    def _sync_charging_status(self) -> None:
        if self._battery_widget is not None and hasattr(self._battery_widget, 'charging'):
            charging = getattr(self._battery_widget, 'charging', False)
            if getattr(self, 'charging', False) != charging:
                self.charging = charging
                self.update()

    def _animate_scale(self, start: float, end: float) -> None:
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        if hasattr(self, '_scale_anim') and self._scale_anim is not None:
            self._scale_anim.stop()
        anim = QPropertyAnimation(self, b"scale")
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self.update)
        anim.finished.connect(lambda: setattr(self, '_scale_anim', None))
        anim.start()
        self._scale_anim = anim

    def _get_gear_path_and_brush(self) -> tuple[QPainterPath, QBrush, float]:
        import math
        from PySide6.QtGui import QPainterPath, QColor, QBrush
        from PySide6.QtCore import QRectF
        gear_d = float(self._size)
        r_outer = gear_d / 2
        r_inner = r_outer * 0.65
        n_teeth = 8
        # Generate symmetric gear path centered at (0,0)
        path = QPainterPath()
        # Bangun path gear tanpa QPainter
        for i in range(n_teeth * 2):
            angle = 2 * math.pi * i / (n_teeth * 2)
            r = r_outer if i % 2 == 0 else r_inner
            px = r * math.cos(angle)
            py = r * math.sin(angle)
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        path.closeSubpath()
        # Center hole
        hole_radius = r_outer * 0.45
        hole = QPainterPath()
        hole.addEllipse(QRectF(-hole_radius, -hole_radius, hole_radius*2, hole_radius*2))
        # Tambahkan lingkaran di antara gigi dan lubang tengah
        mid_radius = (r_outer + hole_radius) / 2
        mid_circle = QPainterPath()
        mid_circle.addEllipse(QRectF(-mid_radius, -mid_radius, mid_radius*2, mid_radius*2))
        gear_with_hole = path.subtracted(hole)
        # Warna dinamis: biru lembut saat charging, putih jika tidak
        charging = getattr(self, 'charging', False)
        if charging:
            bg_color = QColor(90, 167, 255)  # Biru lembut
            outline_color = QColor(90, 167, 255)
        else:
            bg_color = QColor(255, 255, 255)
            outline_color = QColor(255, 255, 255)
        brush = QBrush(bg_color)
        self._outline_color = outline_color
        return gear_with_hole, brush, r_inner

    def setGraphicsEffectOnce(self, effect: QGraphicsDropShadowEffect) -> None:
        # Hindari pembuatan efek berulang, update saja jika sudah ada
        ge = self.graphicsEffect()
        if ge and isinstance(ge, QGraphicsDropShadowEffect):
            ge.setBlurRadius(effect.blurRadius())
            ge.setOffset(effect.offset())
            ge.setColor(effect.color())
        else:
            self.setGraphicsEffect(effect)
    gearHovered = Signal()
    gearUnhovered = Signal()

    def __init__(self, parent: Optional[QWidget] = None, rotation_duration: int = 5000, rotation_direction: int = 1) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._size = 28.175 * 0.8  # ukuran gear tetap
        self._target_size = int(28 * 0.8)
        widget_size = int(28.175 * 0.8) + 16  # tambah ukuran widget lebih besar
        self.setFixedSize(widget_size, widget_size)
        self._scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._scale_anim = None
        self._hovering = False
        self.rotation_duration = rotation_duration
        self.rotation_direction = rotation_direction
        # Tambahkan efek bayangan
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(80, 80, 80, 120))
        self.setGraphicsEffectOnce(shadow)

    def get_rotation(self) -> float:
        return getattr(self, '_rotation', 0.0)

    def set_rotation(self, value: float) -> None:
        self._rotation = value
        self.update()

    from PySide6.QtCore import Property
    rotation = Property(float, get_rotation, set_rotation)

    def get_scale(self) -> float:
        return getattr(self, '_scale', 1.0)

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    from PySide6.QtCore import Property
    scale = Property(float, get_scale, set_scale)

    def enterEvent(self, event: QEnterEvent) -> None:
        if not self._hovering:
            self._hovering = True
            self.gearHovered.emit()
        self._animate_scale(getattr(self, '_scale', 1.0), 1.18)
        # Tooltip dinamis seperti BatteryLogoWidget
        self.setToolTip("Setting")
        from PySide6.QtWidgets import QToolTip
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.toolTip(), self)
        # Animasi rotasi saat hover
        self._rotation_anim = QPropertyAnimation(self, b"rotation")
        self._rotation_anim.setStartValue(getattr(self, '_rotation', 0.0))
        self._rotation_anim.setEndValue(getattr(self, '_rotation', 0.0) + 360.0 * self.rotation_direction)
        self._rotation_anim.setDuration(self.rotation_duration)
        self._rotation_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._rotation_anim.valueChanged.connect(self.update)
        self._rotation_anim.start()
        self._rotation_anim.setLoopCount(-1)
        self._rotation_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._rotation_anim.valueChanged.connect(self.update)
        self._rotation_anim.start()
        # Efek glow saat hover
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 180))
        self.setGraphicsEffectOnce(shadow)
        super(GearIconWidget, self).enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        if self._hovering:
            self._hovering = False
            self.gearUnhovered.emit()
        self._animate_scale(getattr(self, '_scale', 1.18), 1.0)
        # Hilangkan tooltip saat leave
        self.setToolTip("")
        # Stop animasi rotasi saat leave
        if hasattr(self, '_rotation_anim'):
            self._rotation_anim.stop()
        # Kembalikan efek bayangan normal
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(80, 80, 80, 120))
        self.setGraphicsEffectOnce(shadow)
        super(GearIconWidget, self).leaveEvent(event)

    def getGearSize(self):
        return self._size

    def setGearSize(self, value: float):
        self._size = value
        self.update()

    gearSize = Property(float, getGearSize, setGearSize)

    from PySide6.QtGui import QPaintEvent

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center_x = self.width() / 2
        center_y = self.height() / 2
        # ...existing code...
        # Gear logo
        painter.save()
        painter.translate(center_x, center_y)
        painter.scale(getattr(self, '_scale', 1.0), getattr(self, '_scale', 1.0))
        painter.rotate(getattr(self, '_rotation', 0.0))
        path, brush, _ = self._get_gear_path_and_brush()
        outline_color = getattr(self, '_outline_color', QColor(80, 80, 80))
        painter.setPen(QPen(outline_color, 2.5))
        painter.setBrush(brush)
        painter.drawPath(path)
        # Draw mid-circle as a filled semi-transparent gray ring (tidak berubah saat charging)
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainterPath
        gear_d = float(self._size)
        r_outer = gear_d / 2
        hole_radius = r_outer * 0.45
        mid_radius = hole_radius + 0.45
        mid_circle_color = QColor(180, 180, 180, 120)  # Semi-transparent gray
        # Create ring path: outer ellipse minus inner ellipse
        mid_circle_path = QPainterPath()
        mid_circle_path.addEllipse(QRectF(-mid_radius, -mid_radius, mid_radius*2, mid_radius*2))
        mid_circle_path_inner = QPainterPath()
        mid_circle_path_inner.addEllipse(QRectF(-hole_radius, -hole_radius, hole_radius*2, hole_radius*2))
        ring_path = mid_circle_path.subtracted(mid_circle_path_inner)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(mid_circle_color))
        painter.drawPath(ring_path)
        painter.restore()

