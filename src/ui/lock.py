from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from PySide6.QtCore import QEvent, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, Signal, QEasingCurve, Property
from PySide6.QtGui import QBrush, QCloseEvent, QColor, QEnterEvent, QFont, QFontMetrics, QKeyEvent, QLinearGradient, QMouseEvent, QPaintEvent, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QDialog, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget


def get_theme_color(charging: bool) -> str:
    """Return hex color string for charging or not charging state."""
    return "#50B4FF" if charging else "#FFFFFF"


@runtime_checkable
class BatteryWidgetProtocol(Protocol):
    charging: bool

GLASS_STYLE = """
QDialog {
    background: transparent;
    border: none;
}
"""

TOP_BAR_VISUAL_BOTTOM = 55
TOP_BAR_CENTER_ICON_SIZE = 64
TOP_BAR_LOCK_TOP_Y = 0
TOP_BAR_LOCK_TO_WIFI_GAP = 3
TOP_BAR_WIFI_X_OFFSET = -4.35
TOP_BAR_BATTERY_X_OFFSET = 5
TOP_BAR_BATTERY_FROM_WIFI_X = 32
TOP_BAR_KEYCAP_RIGHT_OVERLAP = 3
TOP_BAR_GEAR_GAP = 8
TOP_BAR_CLOCK_GAP = 3.5
TOP_BAR_ICON_HOVER_SCALE = 1.055


def top_bar_center_x(form_width: int, center_icon_width: int = TOP_BAR_CENTER_ICON_SIZE) -> int:
    return int((form_width - center_icon_width) // 2)


def calculate_top_bar_layout(
    *,
    form_width: int,
    center_icon_width: int = TOP_BAR_CENTER_ICON_SIZE,
    keycap_width: int,
    keycap_height: int,
    battery_height: int,
    wifi_height: int,
    gear_width: int | None = None,
    gear_height: int | None = None,
    gear_visual_size: float | None = None,
    clock_width: int | None = None,
    clock_height: int | None = None,
) -> dict[str, int]:
    center_x = top_bar_center_x(form_width, center_icon_width)
    wifi_anchor_x = center_x + center_icon_width + TOP_BAR_LOCK_TO_WIFI_GAP
    battery_anchor_x = wifi_anchor_x + TOP_BAR_BATTERY_FROM_WIFI_X
    keycap_x = center_x - keycap_width + TOP_BAR_KEYCAP_RIGHT_OVERLAP

    layout = {
        "center_x": center_x,
        "center_y": TOP_BAR_LOCK_TOP_Y,
        "keycap_x": int(keycap_x),
        "keycap_y": int(round(TOP_BAR_VISUAL_BOTTOM - keycap_height)),
        "wifi_x": int(wifi_anchor_x + TOP_BAR_WIFI_X_OFFSET),
        "wifi_y": int(round(TOP_BAR_VISUAL_BOTTOM - wifi_height)),
        "battery_x": int(battery_anchor_x + TOP_BAR_BATTERY_X_OFFSET),
        "battery_y": int(round(TOP_BAR_VISUAL_BOTTOM - battery_height)),
    }

    if gear_width is not None and gear_height is not None and gear_visual_size is not None:
        layout["gear_x"] = int(keycap_x - gear_width - TOP_BAR_GEAR_GAP)
        layout["gear_y"] = int(round(TOP_BAR_VISUAL_BOTTOM - ((gear_height + gear_visual_size) / 2)))

    if clock_width is not None and clock_height is not None:
        layout["clock_x"] = int(keycap_x - clock_width - TOP_BAR_CLOCK_GAP)
        layout["clock_y"] = int(round(TOP_BAR_VISUAL_BOTTOM - clock_height))

    return layout

QSS_LABEL_STYLE = """
QLabel[charging="true"] {
    color: #50B4FF;
}
QLabel[charging="false"] {
    color: #FFFFFF;
}
"""

class PremiumTopBarTooltip(QWidget):
    """Small glass tooltip that follows the lock/login top-bar palette."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = ""
        self._charging = False
        self._duration_ms = 900
        self._backdrop = QPixmap()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._reveal)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(130)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def show_text(self, anchor: QWidget, text: str, charging: bool, duration_ms: int = 900) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self._text = text
        self._charging = bool(charging)
        self._duration_ms = duration_ms
        self._hide_timer.stop()
        self.resize(self.sizeHint())

        global_pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 5))
        local_pos = parent.mapFromGlobal(global_pos)
        x = max(8, min(local_pos.x(), parent.width() - self.width() - 8))
        y = max(8, min(local_pos.y(), parent.height() - self.height() - 8))
        self.move(x, y)
        self._capture_backdrop()
        self.update()
        self._show_timer.stop()
        if self.isVisible():
            self._reveal()
        else:
            self._opacity_effect.setOpacity(0.0)
            self._show_timer.start(120)
        self._hide_timer.start(self._duration_ms)

    def _reveal(self) -> None:
        self.raise_()
        self.show()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(float(self._opacity_effect.opacity()))
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def _capture_backdrop(self) -> None:
        parent = self.parentWidget()
        if parent is None or self.width() <= 0 or self.height() <= 0:
            self._backdrop = QPixmap()
            return
        was_visible = self.isVisible()
        if was_visible:
            self.hide()
        source_rect = QRect(self.x(), self.y(), self.width(), self.height()).intersected(parent.rect())
        if source_rect.isEmpty():
            self._backdrop = QPixmap()
            return
        captured = parent.grab(source_rect)
        if captured.isNull():
            self._backdrop = QPixmap()
            return
        small_size = QSize(max(1, captured.width() // 8), max(1, captured.height() // 8))
        softened = captured.scaled(
            small_size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ).scaled(
            captured.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._backdrop = softened

    def sizeHint(self) -> QSize:
        font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        metrics = QFontMetrics(font)
        lines = self._text.splitlines() or [""]
        width = max(metrics.horizontalAdvance(line) for line in lines) + 24
        height = (metrics.height() * len(lines)) + 14
        return QSize(max(86, width), max(30, height))

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        shadow_rect = QRectF(2.2, 2.8, self.width() - 4.4, self.height() - 4.4)
        rect = QRectF(1.3, 1.0, self.width() - 2.6, self.height() - 2.7)
        radius = min(8.0, max(6.0, rect.height() * 0.24))

        wash_core = QColor(255, 255, 255, 30)
        wash_mid = QColor(255, 255, 255, 14)
        wash_edge = QColor(255, 255, 255, 5)
        border_color = QColor(255, 255, 255, 42)
        text_color = QColor(249, 251, 255)
        muted_text = QColor(221, 227, 236, 218)
        shadow = QColor(0, 0, 0, 36)

        cast_shadow = QRadialGradient(QPointF(shadow_rect.center().x(), shadow_rect.bottom() - 1.0), shadow_rect.width() * 0.72)
        cast_shadow.setColorAt(0.0, shadow)
        cast_shadow.setColorAt(0.58, QColor(shadow.red(), shadow.green(), shadow.blue(), max(18, shadow.alpha() // 3)))
        cast_shadow.setColorAt(1.0, QColor(shadow.red(), shadow.green(), shadow.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(cast_shadow))
        painter.drawRoundedRect(shadow_rect, radius + 1.0, radius + 1.0)

        glass_path = QPainterPath()
        glass_path.addRoundedRect(rect, radius, radius)
        painter.save()
        painter.setClipPath(glass_path)
        if not self._backdrop.isNull():
            painter.setOpacity(0.14)
            painter.drawPixmap(rect.toRect(), self._backdrop)
            painter.setOpacity(1.0)
        painter.restore()

        liquid_wash = QRadialGradient(QPointF(rect.left() + rect.width() * 0.34, rect.top() + rect.height() * 0.16), rect.width() * 0.94)
        liquid_wash.setColorAt(0.0, wash_core)
        liquid_wash.setColorAt(0.48, wash_mid)
        liquid_wash.setColorAt(1.0, wash_edge)
        painter.setBrush(QBrush(liquid_wash))
        painter.drawRoundedRect(rect, radius, radius)

        sheen = QLinearGradient(rect.left() + 7.0, rect.top() + 1.0, rect.right() - 6.0, rect.top() + 2.5)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.30, QColor(255, 255, 255, 32))
        sheen.setColorAt(0.52, QColor(255, 255, 255, 8))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(sheen))
        painter.drawRoundedRect(rect.adjusted(4.5, 1.8, -4.5, -self.height() * 0.60), radius - 2.6, radius - 2.6)

        pen = QPen(border_color, 0.52)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        lines = self._text.splitlines() or [""]
        text_rect = self.rect().adjusted(12, 4, -12, -4)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(text_color)
        if len(lines) == 1:
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, lines[0])
        else:
            first_rect = QRect(text_rect.left(), text_rect.top(), text_rect.width(), 13)
            painter.drawText(first_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, lines[0])
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Medium))
            painter.setPen(muted_text)
            rest_rect = QRect(text_rect.left(), text_rect.top() + 13, text_rect.width(), text_rect.height() - 12)
            painter.drawText(rest_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "\n".join(lines[1:]))


def _show_top_bar_tooltip(anchor: QWidget, text: str, charging: bool, duration_ms: int = 900) -> None:
    window = anchor.window()
    tooltip = getattr(window, "_premium_top_bar_tooltip", None)
    if not isinstance(tooltip, PremiumTopBarTooltip):
        tooltip = PremiumTopBarTooltip(window)
        setattr(window, "_premium_top_bar_tooltip", tooltip)
    anchor.setToolTip("")
    anchor.setAccessibleDescription(text)
    tooltip.show_text(anchor, text, charging, duration_ms)


def _hide_top_bar_tooltip(anchor: QWidget) -> None:
    tooltip = getattr(anchor.window(), "_premium_top_bar_tooltip", None)
    if isinstance(tooltip, PremiumTopBarTooltip):
        tooltip._show_timer.stop()
        tooltip.hide()


def _premium_tooltip_text(anchor: QWidget, fallback: str) -> str:
    return anchor.accessibleDescription() or fallback


def show_lock() -> bool:
    """Show authentic Lock Screen dialog and return True if accepted."""
    lock_dialog = AuthenticLockScreen()
    lock_dialog.setModal(True)
    result = lock_dialog.exec()
    return result == QDialog.DialogCode.Accepted

# --- WiFiLogoWidget (restored from backup/src/ui/lock.py) ---
class WiFiLogoWidget(QWidget):
    DISCONNECTED_NAMES = {"", "unknown", "not connected", "tidak diketahui"}

    def __init__(self, parent: Optional[QWidget] = None, battery_widget: Optional[QWidget] = None):
        self.battery_widget: Optional[QWidget] = battery_widget
        self._wifi_name = "Unknown"  # Inisialisasi lebih awal agar selalu ada
        super().__init__(parent)
        if self.battery_widget and hasattr(self.battery_widget, 'timer'):
            self.battery_widget.timer.timeout.connect(self.update)  # type: ignore[attr-defined]
        # Default/base size, will be animated
        self._base_size = 28  # Perbesar ukuran widget Wi-Fi sekitar 30%
        self.setFixedSize(int(self._base_size), int(self._base_size))
        self._scale = 1.0
        self._hovering = False
        self._scale_anim = None  # Ensure _scale_anim can be None
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Enable transparent background so drawing can overflow widget bounds
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._wifi_timer = QTimer(self)
        self._wifi_timer.timeout.connect(self.update_wifi_status)
        self._wifi_timer.start(500)  # refresh setiap 0.5 detik (ideal: responsif & efisien)

    def _is_connected(self) -> bool:
        return self._wifi_name.strip().lower() not in self.DISCONNECTED_NAMES

    def update_wifi_status(self):
        try:
            import subprocess
            result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True)
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
        self._hovering = True
        self._animate_scale(getattr(self, '_scale', 1.0), TOP_BAR_ICON_HOVER_SCALE)
        charging = bool(getattr(self.battery_widget, 'charging', False)) if self.battery_widget is not None else False
        status = self._wifi_name if self._wifi_name else "Unknown"
        _show_top_bar_tooltip(self, f"Wi-Fi : {status}", charging)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self._hovering = False
        self._animate_scale(getattr(self, '_scale', TOP_BAR_ICON_HOVER_SCALE), 1.0)
        _hide_top_bar_tooltip(self)
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        charging = False
        if self.battery_widget and hasattr(self.battery_widget, 'charging'):
            charging = getattr(self.battery_widget, 'charging', False)  # type: ignore[attr-defined]
        if getattr(self, '_hovering', False):
            hover_color = QColor(80, 180, 255, 40) if charging else QColor(255, 255, 255, 22)
            glow = QRadialGradient(QPointF(W / 2, H / 2), min(W, H) * 0.50)
            glow.setColorAt(0.0, hover_color)
            glow.setColorAt(0.62, QColor(hover_color.red(), hover_color.green(), hover_color.blue(), max(6, hover_color.alpha() // 3)))
            glow.setColorAt(1.0, QColor(hover_color.red(), hover_color.green(), hover_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QRectF(2.0, 2.0, W - 4.0, H - 4.0))
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
        connected = self._is_connected()
        if charging and connected:
            base_color = QColor(80, 180, 255, 255)
        elif charging:
            base_color = QColor(176, 222, 242, 255)
        else:
            base_color = QColor(255, 255, 255, 255)
        arc_span = 125
        arc_radii = [icon_W * 0.22]  # lengkungan kecil
        arc_gap = 3
        arc_radii.append(arc_radii[0] + arc_gap)      # lengkungan sedang
        arc_radii.append(arc_radii[1] + arc_gap)      # lengkungan besar
        arc_radii.append(arc_radii[2] + arc_gap)      # lengkungan paling besar (tambahan)

        if connected:
            arc_specs = [(radius, arc_span, 255, 0.0) for radius in arc_radii]
            dot_alpha = 255
        else:
            arc_specs = [
                (arc_radii[0], 118, 182, 0.0),
                (arc_radii[1], 104, 122, 0.0),
                (arc_radii[2], 76, 68, 0.7),
                (arc_radii[3], 58, 42, 1.1),
            ]
            dot_alpha = 158

        for radius, span, alpha, y_offset in arc_specs:
            arc_color = QColor(base_color)
            arc_color.setAlpha(alpha)
            painter.setPen(QPen(arc_color, arc_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(
                int(center_x - radius), int(base_y - radius + y_offset),
                int(2 * radius), int(2 * radius),
                int(90 - span / 2) * 16, int(span * 16)
            )
        dot_radius = 1.5
        arc_bottom_y = base_y + arc_radii[0]
        dot_y = arc_bottom_y
        dot_color = QColor(base_color)
        dot_color.setAlpha(dot_alpha)
        painter.setBrush(dot_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(center_x - dot_radius), int(dot_y - dot_radius), int(2 * dot_radius), int(2 * dot_radius))

# Battery logo widget
class BatteryLogoWidget(QWidget):
    """Widget to display a battery logo with glassmorphism style"""
    chargingChanged = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(int(36.5), 26)
        self.battery_level: float = 1.0
        self.battery_percent: int = 100
        self.charging: bool = False
        self._scale = 1.0
        self._hovering = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Timer untuk update status baterai
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_battery_status)
        self.timer.start(200)  # responsive without excessive power-status polling
        self.update_battery_status()
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
                next_charging = bool(charging) if isinstance(charging, (bool, int)) else False
            else:
                self.battery_percent = 100
                self.battery_level = 1.0
                next_charging = False
        except Exception:
            self.battery_percent = 100
            self.battery_level = 1.0
            next_charging = False
        if next_charging != self.charging:
            self.charging = next_charging
            self.chargingChanged.emit(self.charging)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if getattr(self, '_hovering', False):
            if self.charging:
                glow_color = QColor(80, 180, 255, 38)
            elif self.battery_level <= 0.18:
                glow_color = QColor(255, 205, 126, 28)
            else:
                glow_color = QColor(255, 255, 255, 22)
            glow = QRadialGradient(QPointF(self.width() / 2, self.height() / 2), min(self.width(), self.height()) * 0.55)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(0.72, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(6, glow_color.alpha() // 3)))
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0), 5.0, 5.0)
        # Geser semua gambar ke bawah 0.45 px
        painter.translate(self.width() / 2, self.height() / 2 + 0.45)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        margin = 4.0
        body_rect = QRectF(self.rect()).adjusted(margin, margin, -margin - 1.6, -margin)
        radius = 3.0
        level = max(0.0, min(1.0, float(self.battery_level)))

        low_battery = level <= 0.18 and not self.charging
        low_charging = level <= 0.10 and self.charging

        if low_charging:
            outline_color = QColor(138, 218, 255, 224)
            body_glass_top = QColor(124, 222, 255, 30)
            body_glass_bottom = QColor(255, 201, 118, 10)
            fill_top = QColor(150, 241, 255)
            fill_mid = QColor(76, 202, 255)
            fill_bottom = QColor(72, 144, 239)
            tip_fill = QColor(150, 221, 250, 46)
            track_bottom = QColor(255, 194, 104, 20)
        elif self.charging:
            outline_color = QColor(90, 205, 255, 230)
            body_glass_top = QColor(102, 220, 255, 34)
            body_glass_bottom = QColor(40, 128, 210, 14)
            fill_top = QColor(148, 240, 255)
            fill_mid = QColor(72, 199, 255)
            fill_bottom = QColor(70, 140, 238)
            tip_fill = QColor(82, 190, 244, 52)
            track_bottom = QColor(0, 0, 0, 18)
        elif low_battery:
            outline_color = QColor(255, 214, 138, 218)
            body_glass_top = QColor(255, 218, 150, 22)
            body_glass_bottom = QColor(255, 172, 72, 8)
            fill_top = QColor(255, 232, 178)
            fill_mid = QColor(255, 202, 112)
            fill_bottom = QColor(226, 151, 62)
            tip_fill = QColor(255, 214, 138, 28)
            track_bottom = QColor(0, 0, 0, 18)
        else:
            outline_color = QColor(255, 255, 255, 218)
            body_glass_top = QColor(255, 255, 255, 24)
            body_glass_bottom = QColor(214, 226, 240, 8)
            fill_top = QColor(255, 255, 255)
            fill_mid = QColor(240, 246, 252)
            fill_bottom = QColor(204, 216, 229)
            tip_fill = QColor(255, 255, 255, 28)
            track_bottom = QColor(0, 0, 0, 18)

        body_wash = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.bottom())
        body_wash.setColorAt(0.0, body_glass_top)
        body_wash.setColorAt(1.0, body_glass_bottom)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(body_wash))
        painter.drawRoundedRect(body_rect, radius, radius)

        border = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.bottom())
        border.setColorAt(0.0, QColor(outline_color.red(), outline_color.green(), outline_color.blue(), min(255, outline_color.alpha() + 20)))
        border.setColorAt(1.0, QColor(outline_color.red(), outline_color.green(), outline_color.blue(), max(42, outline_color.alpha() // 2)))
        border_pen = QPen(QBrush(border), 0.68)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(body_rect, radius, radius)

        tip_rect = QRectF(body_rect.right() + 1.9, body_rect.center().y() - 3.2, 1.7, 6.4)
        painter.setPen(border_pen)
        painter.setBrush(QBrush(tip_fill))
        painter.drawRoundedRect(tip_rect, 0.7, 0.7)

        track_rect = body_rect.adjusted(3.0, 3.9, -3.0, -3.9)
        track_wash = QLinearGradient(track_rect.left(), track_rect.top(), track_rect.left(), track_rect.bottom())
        track_wash.setColorAt(0.0, QColor(255, 255, 255, 18))
        track_wash.setColorAt(1.0, track_bottom)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_wash))
        painter.drawRoundedRect(track_rect, 1.9, 1.9)

        fill_width = max(0.0, track_rect.width() * level)
        if fill_width > 0.6:
            fill_rect = QRectF(track_rect.left(), track_rect.top(), fill_width, track_rect.height())
            fill_gradient = QLinearGradient(fill_rect.left(), fill_rect.top(), fill_rect.left(), fill_rect.bottom())
            fill_gradient.setColorAt(0.0, fill_top)
            fill_gradient.setColorAt(0.42, fill_mid)
            fill_gradient.setColorAt(1.0, fill_bottom)
            painter.setBrush(QBrush(fill_gradient))
            painter.drawRoundedRect(fill_rect, 1.8, 1.8)

            sheen = QLinearGradient(fill_rect.left(), fill_rect.top(), fill_rect.left(), fill_rect.top() + fill_rect.height() * 0.55)
            sheen.setColorAt(0.0, QColor(255, 255, 255, 62 if self.charging else 46))
            sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(sheen))
            painter.drawRoundedRect(fill_rect.adjusted(0.7, 0.6, -0.7, -fill_rect.height() * 0.48), 1.2, 1.2)

        if self.charging:
            svg_w = 24.0
            bolt_scale = min(track_rect.width(), track_rect.height()) / svg_w * 1.22
            center = track_rect.center()
            offset_x = center.x() - (12.0 * bolt_scale)
            offset_y = center.y() - (12.0 * bolt_scale)
            points = [
                QPointF(11, 15),
                QPointF(6, 15),
                QPointF(13, 1),
                QPointF(13, 9),
                QPointF(18, 9),
                QPointF(11, 23),
            ]
            points = [QPointF(p.x() * bolt_scale + offset_x, p.y() * bolt_scale + offset_y) for p in points]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 238))
            painter.drawPolygon(points)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovering = True
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.0))
        self._scale_anim.setEndValue(TOP_BAR_ICON_HOVER_SCALE)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        if self.charging and self.battery_percent >= 99:
            state = "Fully charged"
        elif self.charging:
            state = "Charging"
        elif self.battery_level <= 0.18:
            state = "Battery low"
        else:
            state = "Battery"
        tooltip_text = f"{state} : {self.battery_percent}%"
        _show_top_bar_tooltip(self, tooltip_text, self.charging)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        try:
            self._hovering = False
            self._scale_anim = QPropertyAnimation(self, b"scale")
            self._scale_anim.setStartValue(getattr(self, '_scale', TOP_BAR_ICON_HOVER_SCALE))
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.setDuration(220)
            self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._scale_anim.valueChanged.connect(self.update)
            self._scale_anim.start()
            _hide_top_bar_tooltip(self)
            super().leaveEvent(event)
        except KeyboardInterrupt:
            pass
    # Properti scale saja, tanpa rotasi
    # get_scale and set_scale already defined above
    # from PySide6.QtCore import Property
    # scale = Property(float, get_scale, set_scale)
    scale = Property(float, get_scale, set_scale)

def _paint_premium_padlock(
    painter: QPainter,
    bounds: QRectF,
    *,
    charging: bool,
    unlocked: bool,
    hovering: bool,
    lock_color: QColor,
) -> None:
    width = bounds.width()
    height = bounds.height()
    center_x = bounds.center().x()

    if hovering:
        glow_color = QColor(80, 180, 255, 34) if charging else QColor(255, 255, 255, 18)
        glow = QRadialGradient(QPointF(center_x, bounds.top() + height * 0.66), width * 0.40)
        glow.setColorAt(0.0, glow_color)
        glow.setColorAt(0.70, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(5, glow_color.alpha() // 3)))
        glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QRectF(center_x - 22.5, bounds.top() + height * 0.34, 45.0, 36.0))

    body_rect = QRectF(center_x - 12.3, bounds.top() + 35.6, 24.6, 19.8)

    aura_color = QColor(80, 180, 255, 10) if charging else QColor(255, 255, 255, 6)
    aura = QRadialGradient(QPointF(center_x, body_rect.center().y() + 1.4), width * 0.30)
    aura.setColorAt(0.0, aura_color)
    aura.setColorAt(0.62, QColor(aura_color.red(), aura_color.green(), aura_color.blue(), max(2, aura_color.alpha() // 3)))
    aura.setColorAt(1.0, QColor(aura_color.red(), aura_color.green(), aura_color.blue(), 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(aura))
    painter.drawEllipse(QRectF(center_x - 18.0, body_rect.top() - 5.0, 36.0, 33.0))

    if charging:
        body_top = QColor(119, 218, 252, 242)
        body_mid = QColor(72, 164, 239, 238)
        body_bottom = QColor(48, 124, 212, 232)
        shackle_top = QColor(178, 235, 250, 232)
        shackle_bottom = QColor(88, 174, 242, 220)
        edge_color = QColor(196, 243, 255, 82)
        keyhole_dark = QColor(2, 22, 49, 220)
        shackle_depth_color = QColor(4, 29, 60, 78)
        open_leg_depth_color = QColor(4, 29, 60, 46)
    else:
        base = QColor(lock_color)
        body_top = QColor(240, 246, 253, 234)
        body_mid = QColor(max(210, base.red() - 20), max(222, base.green() - 20), max(236, base.blue() - 20), 224)
        body_bottom = QColor(158, 178, 202, 216)
        shackle_top = QColor(240, 248, 255, 220)
        shackle_bottom = QColor(192, 211, 232, 204)
        edge_color = QColor(255, 255, 255, 48)
        keyhole_dark = QColor(13, 22, 34, 218)
        shackle_depth_color = QColor(9, 18, 30, 54)
        open_leg_depth_color = QColor(9, 18, 30, 34)

    shackle_path = QPainterPath()
    open_leg_path = QPainterPath()
    if unlocked:
        left_x = body_rect.left() + 6.7
        right_x = body_rect.right() - 6.7
        shoulder_y = body_rect.top() - 8.4
        crown_y = body_rect.top() - 16.0
        foot_y = body_rect.top() + 1.0
        open_foot_y = body_rect.top() - 6.0
        shackle_path.moveTo(left_x, foot_y)
        shackle_path.lineTo(left_x, shoulder_y)
        shackle_path.cubicTo(
            QPointF(left_x - 0.35, crown_y - 2.9),
            QPointF(right_x + 0.35, crown_y - 2.9),
            QPointF(right_x, shoulder_y),
        )
        open_leg_path.moveTo(right_x, shoulder_y)
        open_leg_path.lineTo(right_x, open_foot_y)
    else:
        left_x = body_rect.left() + 6.7
        right_x = body_rect.right() - 6.7
        crown_y = body_rect.top() - 16.0
        shoulder_y = body_rect.top() - 8.4
        foot_y = body_rect.top() + 1.0
        shackle_path.moveTo(left_x, foot_y)
        shackle_path.lineTo(left_x, shoulder_y)
        shackle_path.cubicTo(
            QPointF(left_x - 0.35, crown_y - 2.9),
            QPointF(right_x + 0.35, crown_y - 2.9),
            QPointF(right_x, shoulder_y),
        )
        shackle_path.lineTo(right_x, foot_y)

    shackle_shadow = QPen(QColor(0, 0, 0, 58 if charging else 48), 4.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    shackle_shadow.setCosmetic(True)
    painter.save()
    painter.translate(0.0, 1.05)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(shackle_shadow)
    painter.drawPath(shackle_path)
    if unlocked:
        open_leg_shadow = QPen(QColor(0, 0, 0, 34 if charging else 28), 3.55, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        open_leg_shadow.setCosmetic(True)
        painter.setPen(open_leg_shadow)
        painter.drawPath(open_leg_path)
    painter.restore()

    shackle_depth = QPen(shackle_depth_color, 3.75, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    shackle_depth.setCosmetic(True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(shackle_depth)
    painter.drawPath(shackle_path)
    if unlocked:
        open_leg_depth = QPen(open_leg_depth_color, 3.35, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        open_leg_depth.setCosmetic(True)
        painter.setPen(open_leg_depth)
        painter.drawPath(open_leg_path)

    shackle_gradient = QLinearGradient(body_rect.left(), body_rect.top() - 18.0, body_rect.left(), body_rect.top() + 2.0)
    shackle_gradient.setColorAt(0.0, shackle_top)
    shackle_gradient.setColorAt(0.56, shackle_top)
    shackle_gradient.setColorAt(1.0, shackle_bottom)
    shackle_pen = QPen(QBrush(shackle_gradient), 2.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    shackle_pen.setCosmetic(True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(shackle_pen)
    painter.drawPath(shackle_path)
    if unlocked:
        painter.setPen(shackle_pen)
        painter.drawPath(open_leg_path)

    shackle_highlight = QPen(QColor(255, 255, 255, 88 if charging else 62), 0.95, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    shackle_highlight.setCosmetic(True)
    painter.save()
    painter.translate(-0.28, -0.42)
    painter.setPen(shackle_highlight)
    painter.drawPath(shackle_path)
    if unlocked:
        painter.drawPath(open_leg_path)
    painter.restore()
    body_shadow = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.bottom() + 2.0)
    body_shadow.setColorAt(0.0, QColor(0, 0, 0, 0))
    body_shadow.setColorAt(0.68, QColor(0, 0, 0, 24 if charging else 18))
    body_shadow.setColorAt(1.0, QColor(0, 0, 0, 58 if charging else 44))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(body_shadow))
    painter.drawRoundedRect(body_rect.adjusted(0.45, 1.05, -0.45, 1.35), 3.4, 3.4)

    body_gradient = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.bottom())
    body_gradient.setColorAt(0.0, body_top)
    body_gradient.setColorAt(0.48, body_mid)
    body_gradient.setColorAt(1.0, body_bottom)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(body_gradient))
    painter.drawRoundedRect(body_rect, 3.4, 3.4)

    body_inner_glow = QRadialGradient(
        QPointF(body_rect.left() + body_rect.width() * 0.34, body_rect.top() + body_rect.height() * 0.22),
        body_rect.width() * 0.86,
    )
    body_inner_glow.setColorAt(0.0, QColor(255, 255, 255, 34 if charging else 26))
    body_inner_glow.setColorAt(0.54, QColor(255, 255, 255, 9 if charging else 7))
    body_inner_glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(QBrush(body_inner_glow))
    painter.drawRoundedRect(body_rect.adjusted(0.7, 0.7, -0.7, -0.7), 2.9, 2.9)

    body_lower_depth = QLinearGradient(body_rect.left(), body_rect.center().y(), body_rect.left(), body_rect.bottom())
    if charging:
        body_lower_depth.setColorAt(0.0, QColor(32, 120, 218, 0))
        body_lower_depth.setColorAt(1.0, QColor(14, 64, 148, 38))
    else:
        body_lower_depth.setColorAt(0.0, QColor(0, 0, 0, 0))
        body_lower_depth.setColorAt(1.0, QColor(18, 27, 38, 30))
    painter.setBrush(QBrush(body_lower_depth))
    painter.drawRoundedRect(body_rect.adjusted(0.8, body_rect.height() * 0.42, -0.8, -0.8), 2.5, 2.5)

    border = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.bottom())
    border.setColorAt(0.0, edge_color)
    border.setColorAt(0.44, QColor(255, 255, 255, 20 if charging else 16))
    border.setColorAt(1.0, QColor(0, 0, 0, 52 if charging else 42))
    border_pen = QPen(QBrush(border), 0.72)
    border_pen.setCosmetic(True)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(border_pen)
    painter.drawRoundedRect(body_rect, 3.4, 3.4)

    top_lip = QPen(QColor(255, 255, 255, 74 if charging else 54), 0.62)
    top_lip.setCosmetic(True)
    painter.setPen(top_lip)
    painter.drawLine(QPointF(body_rect.left() + 3.7, body_rect.top() + 1.35), QPointF(body_rect.right() - 3.7, body_rect.top() + 1.35))

    side_rim = QPen(QColor(255, 255, 255, 22 if charging else 16), 0.42)
    side_rim.setCosmetic(True)
    painter.setPen(side_rim)
    painter.drawLine(QPointF(body_rect.left() + 1.15, body_rect.top() + 4.4), QPointF(body_rect.left() + 1.15, body_rect.bottom() - 4.0))
    painter.drawLine(QPointF(body_rect.right() - 1.15, body_rect.top() + 4.4), QPointF(body_rect.right() - 1.15, body_rect.bottom() - 4.0))

    bottom_lip = QPen(QColor(0, 0, 0, 40 if charging else 30), 0.62)
    bottom_lip.setCosmetic(True)
    painter.setPen(bottom_lip)
    painter.drawLine(QPointF(body_rect.left() + 4.1, body_rect.bottom() - 1.2), QPointF(body_rect.right() - 4.1, body_rect.bottom() - 1.2))

    socket_shadow = QColor(3, 18, 32, 82 if charging else 58)
    socket_highlight = QColor(255, 255, 255, 58 if charging else 38)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(socket_shadow))
    painter.drawRoundedRect(QRectF(body_rect.left() + 5.4, body_rect.top() - 0.35, 2.7, 2.0), 0.8, 0.8)
    painter.drawRoundedRect(QRectF(body_rect.right() - 8.1, body_rect.top() - 0.35, 2.7, 2.0), 0.8, 0.8)
    painter.setBrush(QBrush(socket_highlight))
    if not unlocked:
        painter.drawRoundedRect(QRectF(body_rect.left() + 5.95, body_rect.top() + 0.05, 1.6, 0.65), 0.32, 0.32)
        painter.drawRoundedRect(QRectF(body_rect.right() - 7.55, body_rect.top() + 0.05, 1.6, 0.65), 0.32, 0.32)
    else:
        painter.drawRoundedRect(QRectF(body_rect.left() + 5.95, body_rect.top() + 0.05, 1.6, 0.65), 0.32, 0.32)
        painter.setBrush(QBrush(QColor(0, 0, 0, 54 if charging else 38)))
        painter.drawRoundedRect(QRectF(body_rect.right() - 7.72, body_rect.top() + 0.18, 1.9, 0.58), 0.3, 0.3)

    sheen = QLinearGradient(body_rect.left(), body_rect.top(), body_rect.left(), body_rect.top() + body_rect.height() * 0.55)
    sheen.setColorAt(0.0, QColor(255, 255, 255, 66 if charging else 48))
    sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(sheen))
    painter.drawRoundedRect(body_rect.adjusted(1.2, 1.0, -1.2, -body_rect.height() * 0.52), 2.2, 2.2)

    keyhole = QPainterPath()
    key_center = QPointF(body_rect.center().x(), body_rect.top() + body_rect.height() * 0.48)
    keyhole.addEllipse(QRectF(key_center.x() - 2.05, key_center.y() - 2.25, 4.1, 4.1))
    keyhole.addRoundedRect(QRectF(key_center.x() - 1.0, key_center.y() + 0.7, 2.0, 4.5), 0.65, 0.65)
    keyhole_gradient = QLinearGradient(key_center.x(), key_center.y() - 2.5, key_center.x(), key_center.y() + 5.4)
    keyhole_gradient.setColorAt(0.0, QColor(max(0, keyhole_dark.red() + 8), max(0, keyhole_dark.green() + 12), max(0, keyhole_dark.blue() + 18), min(255, keyhole_dark.alpha() + 4)))
    keyhole_gradient.setColorAt(1.0, keyhole_dark)
    painter.setBrush(QBrush(keyhole_gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(keyhole)

    key_sheen = QColor(255, 255, 255, 46 if charging else 36)
    painter.setBrush(QBrush(key_sheen))
    painter.drawEllipse(QRectF(key_center.x() - 0.65, key_center.y() - 1.0, 1.3, 1.3))

class CustomLockIcon(QWidget):
    def enterEvent(self, event: QEnterEvent):
        self._hovering = True
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.0))
        self._scale_anim.setEndValue(TOP_BAR_ICON_HOVER_SCALE)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        _show_top_bar_tooltip(self, _premium_tooltip_text(self, "Login"), getattr(self, 'charging', False))
        super().enterEvent(event)
    """Custom lock icon widget with iPhone-quality animations"""
    clicked = Signal()

    def __init__(self, color: QColor = QColor(255, 255, 255), parent: Optional[QWidget] = None, charging: bool = False):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("")
        self.setAccessibleDescription("Login")
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
        _hide_top_bar_tooltip(self)
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
        self._scale_anim.setStartValue(getattr(self, '_scale', TOP_BAR_ICON_HOVER_SCALE))
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
        _paint_premium_padlock(
            painter,
            QRectF(0.0, 0.0, float(W), float(H)),
            charging=self.charging,
            unlocked=False,
            hovering=getattr(self, '_hovering', False),
            lock_color=self.lock_color if hasattr(self, 'lock_color') else QColor(255, 255, 255),
        )

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

    def get_lift(self) -> float:
        return getattr(self, '_lift', 0.0)

    def set_lift(self, value: float) -> None:
        self._lift = value
        self.update()

    lift = Property(float, get_lift, set_lift)

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
        self.setToolTip("")
        self.setAccessibleDescription("Exit to Windows")
        self._hover = False
        self._scale = 1.0
        self._lift = 0.0
        self._scale_anim = None
        self._lift_anim = None
        self._collapsed = False  # Status collapse chevron
        self._collapse_progress = 0.0
        self._collapse_anim = None
        self._charging = False
        self._pressing = False
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
        tooltip_text = _premium_tooltip_text(self, "Exit to Windows")
        _show_top_bar_tooltip(self, tooltip_text, self._charging)
        # Efek glow halus saat hover, mengikuti state charging.
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12 if self._charging else 10)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(80, 180, 255, 120) if self._charging else QColor(255, 255, 255, 75))
        self.setGraphicsEffect(shadow)
        # Animasi skala premium yang lebih tenang.
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.0))
        self._scale_anim.setEndValue(1.14)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        self._lift_anim = QPropertyAnimation(self, b"lift")
        self._lift_anim.setStartValue(getattr(self, '_lift', 0.0))
        self._lift_anim.setEndValue(-1.15)
        self._lift_anim.setDuration(220)
        self._lift_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._lift_anim.valueChanged.connect(self.update)
        self._lift_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hover = False
        self._pressing = False
        _hide_top_bar_tooltip(self)
        # Kembalikan efek bayangan normal (abu-abu transparan)
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 45))
        self.setGraphicsEffect(shadow)
        # Animasi skala kembali ke normal
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setStartValue(getattr(self, '_scale', 1.14))
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.valueChanged.connect(self.update)
        self._scale_anim.start()
        self._lift_anim = QPropertyAnimation(self, b"lift")
        self._lift_anim.setStartValue(getattr(self, '_lift', -1.15))
        self._lift_anim.setEndValue(0.0)
        self._lift_anim.setDuration(220)
        self._lift_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._lift_anim.valueChanged.connect(self.update)
        self._lift_anim.start()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = True
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            self._scale_anim = QPropertyAnimation(self, b"scale")
            self._scale_anim.setStartValue(getattr(self, '_scale', 1.14 if self._hover else 1.0))
            self._scale_anim.setEndValue(0.94)
            self._scale_anim.setDuration(120)
            self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._scale_anim.valueChanged.connect(self.update)
            self._scale_anim.start()
            self._lift_anim = QPropertyAnimation(self, b"lift")
            self._lift_anim.setStartValue(getattr(self, '_lift', -1.15 if self._hover else 0.0))
            self._lift_anim.setEndValue(0.35)
            self._lift_anim.setDuration(120)
            self._lift_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._lift_anim.valueChanged.connect(self.update)
            self._lift_anim.start()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = False
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            self._scale_anim = QPropertyAnimation(self, b"scale")
            self._scale_anim.setStartValue(getattr(self, '_scale', 0.94))
            self._scale_anim.setEndValue(1.14 if self._hover else 1.0)
            self._scale_anim.setDuration(140)
            self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._scale_anim.valueChanged.connect(self.update)
            self._scale_anim.start()
            self._lift_anim = QPropertyAnimation(self, b"lift")
            self._lift_anim.setStartValue(getattr(self, '_lift', 0.35))
            self._lift_anim.setEndValue(-1.15 if self._hover else 0.0)
            self._lift_anim.setDuration(140)
            self._lift_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._lift_anim.valueChanged.connect(self.update)
            self._lift_anim.start()
            if not self.underMouse():
                event.accept()
                return
            self._collapsed = not self._collapsed
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
                self._collapse_anim.finished.connect(on_finished)
            self._collapse_anim.start()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.translate(0, getattr(self, '_lift', 0.0))
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
        if self._charging:
            top_color = QColor(126, 232, 255, 244)
            bottom_color = QColor(58, 146, 236, 232)
            shadow_color = QColor(18, 76, 132, 34)
            highlight_color = QColor(236, 252, 255, 38)
        else:
            top_color = QColor(252, 254, 255, 244)
            bottom_color = QColor(198, 209, 221, 230)
            shadow_color = QColor(0, 0, 0, 32)
            highlight_color = QColor(255, 255, 255, 34)
        shadow_pen = QPen(shadow_color, 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(shadow_pen)
        shadow_offset = 0.72
        painter.drawLine(QPointF(x1, y1a + shadow_offset), QPointF(x2, y2a + shadow_offset))
        painter.drawLine(QPointF(x2, y2a + shadow_offset), QPointF(x3, y3a + shadow_offset))
        # Warna gradasi mengikuti status charging dan clock palette
        grad = QLinearGradient(x1, y1a, x3, y3a)
        if self._charging:
            grad.setColorAt(0.0, top_color)
            grad.setColorAt(1.0, bottom_color)
        else:
            grad.setColorAt(0.0, top_color)
            grad.setColorAt(1.0, bottom_color)
        pen = QPen(QBrush(grad), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(x1, y1a), QPointF(x2, y2a))
        painter.drawLine(QPointF(x2, y2a), QPointF(x3, y3a))
        highlight_pen = QPen(highlight_color, 0.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(highlight_pen)
        highlight_offset = -0.45
        painter.drawLine(QPointF(x1, y1a + highlight_offset), QPointF(x2, y2a + highlight_offset))
        painter.drawLine(QPointF(x2, y2a + highlight_offset), QPointF(x3, y3a + highlight_offset))

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
        text_path = QPainterPath()
        path_x: float = x_pos
        for i, char in enumerate(self._text):
            text_path.addText(QPointF(path_x, y_pos), font, char)
            path_x += char_widths[i] + self._letter_spacing
        path_bounds = text_path.boundingRect()
        if self._charging:
            top_color = QColor(119, 218, 252, 242)
            mid_color = QColor(72, 164, 239, 238)
            bottom_color = QColor(48, 124, 212, 230)
            shadow_color = QColor(10, 48, 98, 34)
            highlight_color = QColor(222, 248, 255, 38)
        else:
            top_color = QColor(240, 246, 253, 242)
            mid_color = QColor(218, 228, 240, 236)
            bottom_color = QColor(174, 192, 213, 226)
            shadow_color = QColor(0, 0, 0, 28)
            highlight_color = QColor(255, 255, 255, 34)
        shadow_path = QPainterPath(text_path)
        shadow_path.translate(0.0, 0.58)
        painter.setBrush(QBrush(shadow_color))
        painter.drawPath(shadow_path)
        grad = QLinearGradient(
            path_bounds.left(),
            path_bounds.top(),
            path_bounds.left(),
            path_bounds.bottom(),
        )
        grad.setColorAt(0.0, top_color)
        grad.setColorAt(0.48, mid_color)
        grad.setColorAt(1.0, bottom_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(text_path)
        highlight_path = QPainterPath(text_path)
        highlight_path.translate(0.0, -0.36)
        painter.setBrush(QBrush(highlight_color))
        painter.drawPath(highlight_path)
        painter.restore()

class TimeSeparatorWidget(QWidget):
    """Premium square separator between hour and minute digits."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._charging = False
        self.setFixedSize(28, 28)

    def set_charging(self, charging: bool) -> None:
        self._charging = charging
        self.update()

    def setText(self, text: str) -> None:
        self.setVisible(bool(text))

    def text(self) -> str:
        return "■" if self.isVisible() else ""

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = 14.5
        rect = QRect(
            int((self.width() - side) / 2),
            int((self.height() - side) / 2 + 0.4),
            int(side),
            int(side),
        )
        if self._charging:
            top_color = QColor(119, 218, 252, 224)
            bottom_color = QColor(48, 124, 212, 210)
            shadow_color = QColor(10, 48, 98, 30)
            highlight_color = QColor(222, 248, 255, 34)
        else:
            top_color = QColor(240, 246, 253, 224)
            bottom_color = QColor(174, 192, 213, 208)
            shadow_color = QColor(0, 0, 0, 28)
            highlight_color = QColor(255, 255, 255, 28)
        shadow_rect = QRectF(rect).translated(0.0, 0.58)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRoundedRect(shadow_rect, 0.9, 0.9)
        grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        grad.setColorAt(0.0, top_color)
        grad.setColorAt(1.0, bottom_color)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(rect, 0.9, 0.9)
        highlight_rect = QRect(rect.left(), rect.top(), rect.width(), max(1, int(rect.height() * 0.34)))
        painter.setBrush(QBrush(highlight_color))
        painter.drawRoundedRect(highlight_rect, 0.8, 0.8)
        painter.end()

class PremiumDateLabel(QWidget):
    """Date label painted with the same premium palette family as the clock."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = ""
        self._charging = False
        self.setMinimumHeight(22)

    def setText(self, text: str) -> None:
        self._text = text
        self.updateGeometry()
        self.update()

    def text(self) -> str:
        return self._text

    def set_charging(self, charging: bool) -> None:
        self._charging = charging
        self.update()

    def adjustSize(self) -> None:
        self.resize(self.sizeHint())

    def sizeHint(self):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QFontMetrics
        font = self._font()
        metrics = QFontMetrics(font)
        return QSize(metrics.horizontalAdvance(self._text if self._text else "Wed, 17 May 2026") + 18, metrics.height() + 9)

    def _font(self) -> QFont:
        font = QFont("SF Pro Display")
        font.setPointSizeF(11.7)
        font.setWeight(QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.50)
        return font

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QFontMetrics, QPainterPath
        font = self._font()
        metrics = QFontMetrics(font)
        x = (self.width() - metrics.horizontalAdvance(self._text)) / 2
        y = (self.height() + metrics.ascent() - metrics.descent()) / 2
        text_path = QPainterPath()
        text_path.addText(QPointF(x, y), font, self._text)
        bounds = text_path.boundingRect()
        if self._charging:
            top_color = QColor(146, 226, 255, 232)
            mid_color = QColor(91, 184, 248, 222)
            bottom_color = QColor(58, 138, 224, 216)
            shadow_color = QColor(10, 48, 98, 34)
            highlight_color = QColor(222, 248, 255, 30)
        else:
            top_color = QColor(240, 246, 253, 232)
            mid_color = QColor(218, 228, 240, 222)
            bottom_color = QColor(174, 192, 213, 216)
            shadow_color = QColor(0, 0, 0, 30)
            highlight_color = QColor(255, 255, 255, 28)
        shadow_path = QPainterPath(text_path)
        shadow_path.translate(0.0, 0.58)
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
        highlight_path.translate(0.0, -0.35)
        painter.setBrush(QBrush(highlight_color))
        painter.drawPath(highlight_path)
        painter.end()

class AuthenticLockScreen(QDialog):
    def update_time_label_styles(self, charging: Optional[bool] = None) -> None:
        if charging is None:
            charging = False
            if hasattr(self, 'battery_logo') and self.battery_logo:
                charging = getattr(self.battery_logo, 'charging', False)
        charging = bool(charging)
        required_labels = ("hour_label", "minute_label", "dot_label", "date_label")
        if not all(hasattr(self, label_name) for label_name in required_labels):
            return
        if getattr(self, '_background_charging', None) != charging:
            self._background_charging = charging
            self.update()
        if getattr(self, '_time_charging_state', None) == charging:
            return
        self._time_charging_state = charging

        # Update semua elemen jam sebagai satu paket: jam, menit, separator, dan tanggal.
        self.hour_label.set_charging(charging)
        self.minute_label.set_charging(charging)
        self.dot_label.set_charging(charging)
        self.date_label.set_charging(charging)
        

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
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

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self._background_corner_radius = 22.0
        self._background_charging = False
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
        self.lock_x = top_bar_center_x(self.width(), self.lock_icon.width())
        self.lock_icon.setParent(self)
        self.lock_icon.move(self.lock_x, TOP_BAR_LOCK_TOP_Y)
        self.lock_icon.show()
        # Place unlock icon at same position, but hidden by default
        self.unlock_icon.setParent(self)
        self.unlock_icon.move(self.lock_x, TOP_BAR_LOCK_TOP_Y)
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

        # KeyCapWidget sinkron dengan battery_logo
        self.keycap = KeyCapWidget(self, text="A", battery_widget=self.battery_logo)
        # Gear widget di kiri keycap, jarak harmonis 20px
        self.gear_widget = GearIconWidget(self)
        self.gear_widget.set_battery_widget(self.battery_logo)
        self.wifi_logo = WiFiLogoWidget(self, battery_widget=self.battery_logo)

        top_bar_layout = calculate_top_bar_layout(
            form_width=self.width(),
            center_icon_width=self.lock_icon.width(),
            keycap_width=self.keycap.width(),
            keycap_height=self.keycap.height(),
            battery_height=self.battery_logo.height(),
            wifi_height=self.wifi_logo.height(),
            gear_width=self.gear_widget.width(),
            gear_height=self.gear_widget.height(),
            gear_visual_size=self.gear_widget.getGearSize(),
        )
        self.keycap.move(top_bar_layout["keycap_x"], top_bar_layout["keycap_y"])
        self.keycap.show()
        self.gear_widget.move(top_bar_layout["gear_x"], top_bar_layout["gear_y"])
        self.gear_widget.show()

        # Declare missing attributes for lint compliance
        self.time_label: QLabel = QLabel(self)
        self.unlock_text: QLabel = QLabel(self)
        # Restore battery logo to visible top position
        # Calculate battery logo position just above red line
        # Use garis1_y from paintEvent and battery_logo.height() for placement
        self.battery_logo.setParent(self)
        self.battery_logo.move(top_bar_layout["battery_x"], top_bar_layout["battery_y"])
        self.battery_logo.show()

        # WiFi logo widget baru di sebelah kanan gembok, jarak 30px
        self.wifi_logo.move(top_bar_layout["wifi_x"], top_bar_layout["wifi_y"])
        self.wifi_logo.show()

        # Hitung dan print jarak dari bawah widget logo WiFi ke garis merah
        # Connect padlock click to show login
        self.lock_icon.clicked.connect(self.show_login_form)
        # Create date label
        self.date_label = PremiumDateLabel(self)
        self.time_container = QWidget(self)
        self.time_layout = QHBoxLayout(self.time_container)
        self.time_layout.setContentsMargins(0, 0, 0, 0)
        self.time_layout.setSpacing(0)
        
        # Gunakan TimeVerticalStretchLabel untuk jam dan menit dengan vertical stretch + horizontal compression
        from PySide6.QtGui import QFont
        self.hour_label = TimeVerticalStretchLabel(
            parent=self,
            font_size=108.0,
            font_weight=QFont.Weight.ExtraLight,
            letter_spacing=12.0,
            vertical_scale=2.95,
            horizontal_scale=0.66
        )
        self.minute_label = TimeVerticalStretchLabel(
            parent=self,
            font_size=108.0,
            font_weight=QFont.Weight.ExtraLight,
            letter_spacing=12.0,
            vertical_scale=2.95,
            horizontal_scale=0.66
        )
        
        # SOLUSI Z-ORDER: Buat label jam transparan untuk mouse events
        # Clock tetap visible tapi tidak menghalangi click pada widget lain
        self.hour_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.minute_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.dot_label = TimeSeparatorWidget(self)
        # Style jam dan menit dengan warna off-white dan shadow
        # Style jam digital besar (jam, titik, menit) di bawah tanggal
        # hour_label dan minute_label sudah diatur oleh TimeVerticalStretchLabel
        
        # SOLUSI Z-ORDER: Dot label juga transparan untuk mouse events
        self.dot_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.date_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    # (rollback: hapus pewarnaan dinamis label jam)

        # Separator clock is custom-painted with its own subtle shadow.
        
        # Set alignment untuk semua label
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
        self._time_charging_state: Optional[bool] = None
        self.battery_logo.chargingChanged.connect(self.update_time_label_styles)
        
        # Update time and date
        self.update_time_date()
        self.update_time_label_styles()
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
        chevron_y = int(y_garis_bawah - 4)  # naikkan sedikit agar ruang bawah lebih seimbang
        self.chevron_exit.move(chevron_x, chevron_y)
        self.chevron_exit.show()
        
        # SOLUSI Z-ORDER: Chevron exit juga harus di depan
        self.chevron_exit.raise_()
    def show_login_form(self):
        try:
            # Alur sederhana: klik gembok menutup lock screen,
            # lalu main.py akan membuka form login.
            self.accept()
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
        gap_below_gembok = 20  # Turunkan label tanggal sedikit lebih jauh dari gembok
        gap_below_date = -118  # Compact but less forced, preserving date/clock rhythm
        vertical_offset_down = 30  # Turunkan blok tanggal + jam ke bawah
        time_offset_down = 24  # Turunkan jam besar ke bawah
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
    TOOLTIP_DURATION_MS = 850
    KEYBOARD_POLL_MS = 80

    def _state_tooltip_text(self) -> str:
        caps_status = "On" if self._capslock_on else "Off"
        shift_status = "On" if self._shift_on else "Off"
        return f"CapsLock : {caps_status}\nShift : {shift_status}"

    def _show_state_tooltip(self) -> None:
        tooltip_text = self._state_tooltip_text()
        _show_top_bar_tooltip(self, tooltip_text, getattr(self, 'charging', False), self.TOOLTIP_DURATION_MS)

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
        self._hovering = True
        self._animate_scale(getattr(self, '_scale', 1.0), TOP_BAR_ICON_HOVER_SCALE)
        self._show_state_tooltip()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovering = False
        self._animate_scale(getattr(self, '_scale', TOP_BAR_ICON_HOVER_SCALE), 1.0)
        _hide_top_bar_tooltip(self)
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
        self._timer.start(self.KEYBOARD_POLL_MS)
        self._poll_keyboard_state()
        self.charging = False
        self._hovering = False
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
                self.setAccessibleDescription(self._state_tooltip_text())
                if getattr(self, '_hovering', False):
                    self._show_state_tooltip()
        except Exception:
            pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if getattr(self, '_hovering', False):
            glow_color = QColor(80, 180, 255, 34) if getattr(self, 'charging', False) else QColor(255, 255, 255, 18)
            glow = QRadialGradient(QPointF(self.width() / 2, self.height() / 2), min(self.width(), self.height()) * 0.54)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(0.70, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(5, glow_color.alpha() // 3)))
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(QRectF(3.0, 3.0, self.width() - 6.0, self.height() - 6.0), 5.0, 5.0)
        scale = getattr(self, '_scale', 1.0)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(scale, scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        rect = QRectF(self.rect()).adjusted(4.2, 7.9, -4.2, -4.4)
        radius = 2.8
        charging = getattr(self, 'charging', False)

        if charging:
            outline_color = QColor(126, 214, 255, 224)
            body_top = QColor(105, 218, 255, 34)
            body_bottom = QColor(42, 132, 216, 16)
            inactive_color = QColor(132, 215, 255, 176)
            active_color = QColor(255, 255, 255, 242)
            active_glow = QColor(80, 180, 255, 68)
        else:
            outline_color = QColor(255, 255, 255, 220)
            body_top = QColor(255, 255, 255, 30)
            body_bottom = QColor(205, 218, 232, 11)
            inactive_color = QColor(235, 242, 250, 194)
            active_color = QColor(80, 180, 255, 238)
            active_glow = QColor(80, 180, 255, 54)

        body_wash = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        body_wash.setColorAt(0.0, body_top)
        body_wash.setColorAt(1.0, body_bottom)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(body_wash))
        painter.drawRoundedRect(rect, radius, radius)

        inner_rect = rect.adjusted(1.35, 1.25, -1.35, -1.25)
        inner_pen = QPen(QColor(255, 255, 255, 24 if charging else 22), 0.34)
        inner_pen.setCosmetic(True)
        painter.setPen(inner_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner_rect, max(1.4, radius - 1.1), max(1.4, radius - 1.1))

        divider_x = rect.left() + rect.width() * 0.34
        if self._capslock_on:
            cap_area = QRectF(rect.left() + 1.0, rect.top() + 1.0, divider_x - rect.left() - 1.55, rect.height() - 2.0)
            cap_wash = QLinearGradient(cap_area.left(), cap_area.top(), cap_area.left(), cap_area.bottom())
            cap_wash.setColorAt(0.0, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), 28))
            cap_wash.setColorAt(1.0, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), 4))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(cap_wash))
            painter.drawRoundedRect(cap_area, 1.8, 1.8)

        if self._shift_on:
            shift_area = QRectF(divider_x + 0.65, rect.top() + 1.0, rect.right() - divider_x - 1.65, rect.height() - 2.0)
            shift_wash = QLinearGradient(shift_area.left(), shift_area.top(), shift_area.left(), shift_area.bottom())
            shift_wash.setColorAt(0.0, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), 24))
            shift_wash.setColorAt(1.0, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), 4))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(shift_wash))
            painter.drawRoundedRect(shift_area, 1.8, 1.8)

        border = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        border.setColorAt(0.0, QColor(outline_color.red(), outline_color.green(), outline_color.blue(), min(255, outline_color.alpha() + 22)))
        border.setColorAt(1.0, QColor(outline_color.red(), outline_color.green(), outline_color.blue(), max(50, outline_color.alpha() // 2)))
        border_pen = QPen(QBrush(border), 0.66)
        border_pen.setCosmetic(True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)

        top_sheen = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top() + rect.height() * 0.50)
        top_sheen.setColorAt(0.0, QColor(255, 255, 255, 32 if charging else 28))
        top_sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(top_sheen))
        painter.drawRoundedRect(rect.adjusted(1.1, 0.9, -1.1, -rect.height() * 0.58), 2.0, 2.0)

        divider = QLinearGradient(divider_x, rect.top() + 2.1, divider_x, rect.bottom() - 2.1)
        divider.setColorAt(0.0, QColor(255, 255, 255, 0))
        divider.setColorAt(0.45, QColor(outline_color.red(), outline_color.green(), outline_color.blue(), 58 if charging else 46))
        divider.setColorAt(1.0, QColor(255, 255, 255, 0))
        divider_pen = QPen(QBrush(divider), 0.46)
        divider_pen.setCosmetic(True)
        painter.setPen(divider_pen)
        painter.drawLine(QPointF(divider_x, rect.top() + 2.1), QPointF(divider_x, rect.bottom() - 2.1))

        led_center = QPointF(rect.left() + (divider_x - rect.left()) * 0.50, rect.top() + 4.05)
        led_radius = 1.58
        if self._capslock_on:
            led_color = QColor(active_color)
            led_ring = QColor(active_glow)
        else:
            led_color = QColor(inactive_color)
            led_color.setAlpha(124 if charging else 140)
            led_ring = QColor(inactive_color)
            led_ring.setAlpha(54)
        painter.setPen(Qt.PenStyle.NoPen)
        if self._capslock_on:
            glow = QRadialGradient(led_center, 5.0)
            glow.setColorAt(0.0, active_glow)
            glow.setColorAt(0.72, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), max(10, active_glow.alpha() // 4)))
            glow.setColorAt(1.0, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), 0))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QRectF(led_center.x() - 4.3, led_center.y() - 4.3, 8.6, 8.6))
        ring_pen = QPen(led_ring, 0.55)
        ring_pen.setCosmetic(True)
        painter.setPen(ring_pen)
        painter.setBrush(QBrush(led_color))
        painter.drawEllipse(QRectF(led_center.x() - led_radius, led_center.y() - led_radius, led_radius * 2, led_radius * 2))

        arrow_color = QColor(active_color if self._shift_on else inactive_color)
        if not self._shift_on:
            arrow_color.setAlpha(162 if charging else 178)
        arrow_center = QPointF((divider_x + rect.right()) * 0.50 + 0.55, rect.center().y() + 1.55)
        arrow_path = QPainterPath()
        arrow_path.moveTo(arrow_center.x(), arrow_center.y() - 5.85)
        arrow_path.lineTo(arrow_center.x() - 4.05, arrow_center.y() - 1.55)
        arrow_path.lineTo(arrow_center.x() - 1.38, arrow_center.y() - 1.55)
        arrow_path.lineTo(arrow_center.x() - 1.38, arrow_center.y() + 4.0)
        arrow_path.lineTo(arrow_center.x() + 1.38, arrow_center.y() + 4.0)
        arrow_path.lineTo(arrow_center.x() + 1.38, arrow_center.y() - 1.55)
        arrow_path.lineTo(arrow_center.x() + 4.05, arrow_center.y() - 1.55)
        arrow_path.closeSubpath()

        if self._shift_on:
            shift_glow = QRadialGradient(arrow_center, 10.0)
            shift_glow.setColorAt(0.0, active_glow)
            shift_glow.setColorAt(0.68, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), max(8, active_glow.alpha() // 4)))
            shift_glow.setColorAt(1.0, QColor(active_glow.red(), active_glow.green(), active_glow.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(shift_glow))
            painter.drawEllipse(QRectF(arrow_center.x() - 8.2, arrow_center.y() - 8.0, 16.4, 16.0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(arrow_color))
        painter.drawPath(arrow_path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        edge_pen = QPen(QColor(255, 255, 255, 36 if self._shift_on else 20), 0.28)
        edge_pen.setCosmetic(True)
        painter.setPen(edge_pen)
        painter.drawPath(arrow_path)

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
        from PySide6.QtGui import QPainterPath, QColor, QBrush, QRadialGradient
        from PySide6.QtCore import QRectF
        gear_d = float(self._size)
        r_outer = gear_d / 2
        r_inner = r_outer * 0.76
        n_teeth = 8
        path = QPainterPath()
        points: list[tuple[float, float, float]] = []
        for tooth in range(n_teeth):
            center = 2 * math.pi * tooth / n_teeth
            for offset, radius in (
                (-0.36, r_inner),
                (-0.18, r_outer),
                (0.18, r_outer),
                (0.36, r_inner),
            ):
                angle = center + (2 * math.pi / n_teeth) * offset
                points.append((angle, radius, 0.0))

        for i, (angle, radius, _) in enumerate(points):
            px = radius * math.cos(angle)
            py = radius * math.sin(angle)
            if i == 0:
                path.moveTo(px, py)
            else:
                prev_angle, prev_radius, _ = points[i - 1]
                delta = angle - prev_angle
                c1_angle = prev_angle + delta * 0.48
                c2_angle = angle - delta * 0.48
                c1_radius = prev_radius + (radius - prev_radius) * 0.36
                c2_radius = radius - (radius - prev_radius) * 0.36
                c1 = QPointF(c1_radius * math.cos(c1_angle), c1_radius * math.sin(c1_angle))
                c2 = QPointF(c2_radius * math.cos(c2_angle), c2_radius * math.sin(c2_angle))
                path.cubicTo(c1, c2, QPointF(px, py))

        first_angle, first_radius, _ = points[0]
        last_angle, last_radius, _ = points[-1]
        first = QPointF(first_radius * math.cos(first_angle), first_radius * math.sin(first_angle))
        last_angle_adjusted = last_angle
        first_angle_adjusted = first_angle + 2 * math.pi
        delta = first_angle_adjusted - last_angle_adjusted
        c1_angle = last_angle_adjusted + delta * 0.48
        c2_angle = first_angle_adjusted - delta * 0.48
        c1_radius = last_radius + (first_radius - last_radius) * 0.36
        c2_radius = first_radius - (first_radius - last_radius) * 0.36
        path.cubicTo(
            QPointF(c1_radius * math.cos(c1_angle), c1_radius * math.sin(c1_angle)),
            QPointF(c2_radius * math.cos(c2_angle), c2_radius * math.sin(c2_angle)),
            first,
        )
        path.closeSubpath()
        hole_radius = r_outer * 0.38
        hole = QPainterPath()
        hole.addEllipse(QRectF(-hole_radius, -hole_radius, hole_radius*2, hole_radius*2))
        gear_with_hole = path.subtracted(hole)
        charging = getattr(self, 'charging', False)
        if charging:
            fill_core = QColor(126, 220, 255, 208)
            fill_edge = QColor(56, 146, 232, 174)
            outline_color = QColor(152, 226, 255, 188)
        else:
            fill_core = QColor(255, 255, 255, 204)
            fill_edge = QColor(206, 218, 232, 168)
            outline_color = QColor(255, 255, 255, 176)
        gradient = QRadialGradient(QPointF(-r_outer * 0.20, -r_outer * 0.25), r_outer * 1.25)
        gradient.setColorAt(0.0, fill_core)
        gradient.setColorAt(0.58, QColor(fill_core.red(), fill_core.green(), fill_core.blue(), max(130, fill_core.alpha() - 28)))
        gradient.setColorAt(1.0, fill_edge)
        brush = QBrush(gradient)
        self._outline_color = outline_color
        self._hole_radius = hole_radius
        self._ring_color = QColor(outline_color.red(), outline_color.green(), outline_color.blue(), 68 if charging else 60)
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
        self._size = 28.175 * 0.77
        self._target_size = int(28 * 0.8)
        widget_size = int(28.175 * 0.8) + 16  # tambah ukuran widget lebih besar
        self.setFixedSize(widget_size, widget_size)
        self._scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._scale_anim = None
        self._hovering = False
        self.rotation_duration = rotation_duration
        self.rotation_direction = rotation_direction
        # Hover/idle effect is painted inside the widget to avoid translucent-window dirty regions.

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
        self._animate_scale(getattr(self, '_scale', 1.0), TOP_BAR_ICON_HOVER_SCALE)
        tooltip_text = "Settings"
        _show_top_bar_tooltip(self, tooltip_text, getattr(self, 'charging', False))
        # Animasi rotasi saat hover
        self._rotation_anim = QPropertyAnimation(self, b"rotation")
        self._rotation_anim.setStartValue(getattr(self, '_rotation', 0.0))
        self._rotation_anim.setEndValue(getattr(self, '_rotation', 0.0) + 60.0 * self.rotation_direction)
        self._rotation_anim.setDuration(260)
        self._rotation_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._rotation_anim.valueChanged.connect(self.update)
        self._rotation_anim.start()
        super(GearIconWidget, self).enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        if self._hovering:
            self._hovering = False
            self.gearUnhovered.emit()
        self._animate_scale(getattr(self, '_scale', TOP_BAR_ICON_HOVER_SCALE), 1.0)
        _hide_top_bar_tooltip(self)
        # Stop animasi rotasi saat leave
        if hasattr(self, '_rotation_anim'):
            self._rotation_anim.stop()
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
        if getattr(self, '_hovering', False):
            glow_color = QColor(80, 180, 255, 26) if getattr(self, 'charging', False) else QColor(255, 255, 255, 15)
            glow = QRadialGradient(QPointF(center_x, center_y), min(self.width(), self.height()) * 0.45)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(0.72, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(5, glow_color.alpha() // 3)))
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QRectF(5.0, 5.0, self.width() - 10.0, self.height() - 10.0))
        # Gear logo
        painter.save()
        painter.translate(center_x, center_y)
        painter.scale(getattr(self, '_scale', 1.0), getattr(self, '_scale', 1.0))
        painter.rotate(getattr(self, '_rotation', 0.0))
        path, brush, _ = self._get_gear_path_and_brush()
        outline_color = getattr(self, '_outline_color', QColor(80, 80, 80))
        outline_pen = QPen(outline_color, 0.82)
        outline_pen.setCosmetic(True)
        outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outline_pen)
        painter.setBrush(brush)
        painter.drawPath(path)
        from PySide6.QtGui import QPainterPath
        gear_d = float(self._size)
        r_outer = gear_d / 2
        hole_radius = getattr(self, '_hole_radius', r_outer * 0.38)
        mid_radius = hole_radius + 0.72
        mid_circle_path = QPainterPath()
        mid_circle_path.addEllipse(QRectF(-mid_radius, -mid_radius, mid_radius*2, mid_radius*2))
        mid_circle_path_inner = QPainterPath()
        mid_circle_path_inner.addEllipse(QRectF(-hole_radius, -hole_radius, hole_radius*2, hole_radius*2))
        ring_path = mid_circle_path.subtracted(mid_circle_path_inner)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(getattr(self, '_ring_color', QColor(255, 255, 255, 72))))
        painter.drawPath(ring_path)
        highlight = QPainterPath()
        highlight.addEllipse(QRectF(-r_outer * 0.42, -r_outer * 0.48, r_outer * 0.84, r_outer * 0.84))
        painter.setBrush(QBrush(QColor(255, 255, 255, 20 if getattr(self, 'charging', False) else 18)))
        painter.drawPath(highlight.intersected(path))
        painter.restore()

