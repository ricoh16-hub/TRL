import os
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QBrush
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QToolButton, QVBoxLayout, QWidget
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

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


# Modern almond-shaped eye icon with iris, pupil, and highlight
def _draw_eye_icon(
    size: int = 24,
    iris_color: QColor = QColor(80, 180, 255),
    pupil_color: QColor = QColor(30, 30, 30),
    highlight_color: QColor = QColor(255, 255, 255),
    crossed: bool = False,
    outline_color: QColor = QColor(60, 60, 60)
) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Almond (eye) outline
    outline_pen = QPen(outline_color, 1.5)
    painter.setPen(outline_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    margin = size * 0.13
    path.moveTo(margin, size // 2)
    path.quadTo(size // 2, margin, size - margin, size // 2)
    path.quadTo(size // 2, size - margin, margin, size // 2)
    painter.drawPath(path)

    # Pupil dan highlight selalu digambar, baik mata terbuka maupun tertutup
    center = (size / 2, size / 2)
    pupil_radius = size * 0.10
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(pupil_color))
    painter.drawEllipse(
        int(center[0] - pupil_radius),
        int(center[1] - pupil_radius),
        int(pupil_radius * 2),
        int(pupil_radius * 2)
    )

    highlight_w = size * 0.08
    highlight_h = size * 0.04
    painter.setBrush(QBrush(highlight_color))
    painter.drawEllipse(
        int(center[0] - pupil_radius * 0.5),
        int(center[1] - pupil_radius * 0.5),
        int(highlight_w),
        int(highlight_h)
    )

    if crossed:
        # Mata tertutup: tambahkan garis miring (backslash) dari kiri atas ke kanan bawah
        slash_pen = QPen(outline_color, 1.5)
        painter.setPen(slash_pen)
        margin = size * 0.13
        painter.drawLine(int(margin), int(margin), int(size - margin), int(size - margin))
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



def _draw_check_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)  # type: ignore
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    stroke = 1.5
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawRoundedRect(
        int(size * 0.14), int(size * 0.14), int(size * 0.72), int(size * 0.72), int(size * 0.16), int(size * 0.16)
    )
    path = QPainterPath()
    path.moveTo(size * 0.28, size * 0.53)
    path.lineTo(size * 0.44, size * 0.68)
    path.lineTo(size * 0.74, size * 0.36)
    painter.drawPath(path)

    painter.end()
    return pixmap


def _set_icon(label: QLabel, pixmap: QPixmap) -> None:
    label.setPixmap(pixmap)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)


def _apply_action_button_theme(cancel_btn: CustomButton, submit_btn: CustomButton, charging: bool) -> None:
    cancel_btn.setPrimary(False)
    submit_btn.setPrimary(False)

    def _set_button_shadow(button: CustomButton, color: QColor, blur: int, offset_y: int) -> None:
        shadow = QGraphicsDropShadowEffect(button)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset_y)
        shadow.setColor(color)
        button.setGraphicsEffect(shadow)

    if charging:
        # Buat kedua tombol seragam dengan gradien dan warna yang sama
        common_gradient = (QColor("#1F6FAF"), QColor("#43A8E8"))
        common_hover_gradient = (QColor("#2B83C9"), QColor("#5BBEFF"))
        common_border = QColor(105, 195, 255, 165)
        common_text_color = QColor("#FFFFFF")
        common_shadow = QColor(80, 180, 255, 88)

        cancel_btn._custom_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_gradient = common_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_hover_gradient = common_hover_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_border = common_border  # type: ignore[attr-defined]
        cancel_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]

        submit_btn._custom_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_gradient = common_gradient  # type: ignore[attr-defined]
        submit_btn._custom_hover_gradient = common_hover_gradient  # type: ignore[attr-defined]
        submit_btn._custom_border = common_border  # type: ignore[attr-defined]
        submit_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]

        _set_button_shadow(cancel_btn, common_shadow, 13, 2)
        _set_button_shadow(submit_btn, common_shadow, 13, 2)
    else:
        common_gradient = (QColor("#164F63"), QColor("#248FA0"))
        common_hover_gradient = (QColor("#1E657A"), QColor("#35D6E7"))
        common_border = QColor(53, 214, 231, 145)
        common_text_color = QColor("#FFFFFF")
        common_shadow = QColor(53, 214, 231, 70)

        cancel_btn._custom_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        cancel_btn._custom_gradient = common_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_hover_gradient = common_hover_gradient  # type: ignore[attr-defined]
        cancel_btn._custom_border = common_border  # type: ignore[attr-defined]
        cancel_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]

        submit_btn._custom_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_hover_bg = None  # type: ignore[attr-defined]
        submit_btn._custom_gradient = common_gradient  # type: ignore[attr-defined]
        submit_btn._custom_hover_gradient = common_hover_gradient  # type: ignore[attr-defined]
        submit_btn._custom_border = common_border  # type: ignore[attr-defined]
        submit_btn._custom_text_color = common_text_color  # type: ignore[attr-defined]

        _set_button_shadow(cancel_btn, common_shadow, 13, 2)
        _set_button_shadow(submit_btn, common_shadow, 13, 2)

    cancel_btn.update()
    submit_btn.update()


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
            "accent": "#35D6E7",
            "accent_rgb": "53, 214, 231",
            "border_alpha": "0.34",
            "panel_bg0": "#10263D",
            "panel_bg1": "#24445F",
        },
        True: {
            "accent": "#50B4FF",
            "accent_rgb": "80, 180, 255",
            "border_alpha": "0.38",
            "panel_bg0": "rgba(8, 20, 65, 0.96)",
            "panel_bg1": "rgba(16, 36, 98, 0.96)",
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

    def _set_charging(self, charging: bool) -> None:
        if self._charging == charging:
            return
        self._charging = charging
        self._palette = self._resolve_palette(charging)
        self._accent = QColor(self._palette["accent"])
        self._accent_rgb = self._palette["accent_rgb"]
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
        if self._visual_mode == "pin":
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
        title_rgb = self._accent_rgb if self._visual_mode == "pin" else "244, 248, 255"
        title_alpha = (
            self._palette.get("headline_alpha", "0.92")
            if self._visual_mode == "pin"
            else "0.74"
        )
        title_bar_bg_rgb = self._accent_rgb if self._visual_mode == "pin" else "255, 255, 255"
        title_bar_bg_alpha = self._palette.get("title_bar_alpha", "0.050" if self._visual_mode == "pin" else "0.025")
        close_hover_rgb = self._palette.get("close_hover_rgb", self._accent_rgb)
        close_hover_border_rgb = close_hover_rgb if self._visual_mode == "pin" else "255, 255, 255"
        close_hover_border_alpha = self._palette.get("close_hover_border_alpha", "0.58" if self._visual_mode == "pin" else "0.18")
        close_hover_bg_rgb = close_hover_rgb if self._visual_mode == "pin" else "255, 255, 255"
        close_hover_bg_alpha = self._palette.get("close_hover_bg_alpha", "0.115" if self._visual_mode == "pin" else "0.052")
        close_pressed_bg_rgb = close_hover_rgb if self._visual_mode == "pin" else "255, 255, 255"
        close_pressed_bg_alpha = self._palette.get("close_pressed_bg_alpha", "0.18" if self._visual_mode == "pin" else "0.085")
        message_rgb = self._accent_rgb if self._visual_mode == "pin" else "244, 248, 255"
        message_alpha = (
            self._palette.get("message_alpha", "0.86")
            if self._visual_mode == "pin"
            else self._palette.get("message_alpha", "0.80")
        )
        self.setStyleSheet(f"""
            QDialog#credentialsWarningDialog {{
                background: transparent;
            }}
            QFrame#warningPanel {{
                border: 1px solid rgba({self._accent_rgb}, {self._palette["border_alpha"]});
                border-radius: {self.RADIUS}px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self._palette["panel_bg0"]},
                    stop:1 {self._palette["panel_bg1"]}
                );
            }}
            QFrame#warningTitleBar {{
                border: none;
                background: rgba({title_bar_bg_rgb}, {title_bar_bg_alpha});
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
                font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
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
                font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
            }}
            QLabel#warningMessage {{
                color: rgba({message_rgb}, {message_alpha});
                font-size: 12px;
                font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
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

        self._panel = QFrame(self)
        self._panel.setObjectName("warningPanel")
        panel_layout = QVBoxLayout(self._panel)
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
        close_icon_color = QColor(self._accent) if self._visual_mode == "pin" else QColor(244, 248, 255, 185)
        if self._visual_mode == "pin":
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
        if self._visual_mode == "pin":
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


def show_credentials_login(app: QApplication, pin_user: User, parent: Optional[QWidget] = None) -> Optional[User]:
    """Step 2: username/password validation after successful PIN step."""
    dialog = QDialog(parent)
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
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {bg0},
                stop:1 {bg1}
            );
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.18);
        }}
        QLabel {{
            color: #f4f8ff;
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
            font-size: 13px;
        }}
        QFrame#cardPanel {{
            border: 1px solid {card_border};
            border-radius: 20px;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {card_bg0},
                stop:1 {card_bg1}
            );
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
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
        }}
        QFrame#inputRow {{
            border: 1px solid {input_border};
            border-radius: 12px;
            background: {input_row_bg};
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
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
        }}
        QLineEdit#fieldInput::placeholder {{
            color: rgba(214, 228, 255, 0.42);
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
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
        }}
    """

    # Samakan background utama dengan login.py (charging & tidak charging)
    _STYLE_NORMAL = _BASE_SHEET.format(
        bg0="#222a36", bg1="#3a4a5c",
        card_border="rgba(53, 214, 231, 0.42)",
        card_bg0="#10263D", card_bg1="#24445F",
        glow="rgba(53, 214, 231, 0.72)",
        label_color="#FFFFFF",
        input_border="rgba(53, 214, 231, 0.32)",
        input_row_bg=(
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1, "
            "stop:0 rgba(16, 38, 61, 0.70), "
            "stop:1 rgba(36, 68, 95, 0.52)"
            ")"
        ),
        status_color="#FFFFFF",
        cancel_border="#D3D3D3",
        cancel_color="#333333",
        submit_border="#D3D3D3",
        submit0="#C0C0C0", submit1="#E8E8E8",
        submit_h0="#E8E8E8", submit_h1="#FFFFFF",
    )

    _STYLE_CHARGING = _BASE_SHEET.format(
        bg0="#222a36", bg1="#3a4a5c",  # sama persis login.py
        card_border="rgba(80, 180, 255, 0.55)",
        card_bg0="rgba(8, 20, 65, 0.90)", card_bg1="rgba(16, 36, 98, 0.90)",
        glow="rgba(80, 180, 255, 0.95)",
        label_color="rgba(80, 180, 255, 0.90)",
        input_border="rgba(80, 180, 255, 0.42)",
        input_row_bg="rgba(18, 33, 83, 0.68)",
        status_color="rgba(80, 200, 255, 0.90)",
        cancel_border="rgba(80, 180, 255, 0.40)",
        cancel_color="#50B4FF",
        submit_border="rgba(80, 180, 255, 0.45)",
        submit0="#0d72cc", submit1="#50B4FF",
        submit_h0="#1580dc", submit_h1="#7dd8ff",
    )

    _TITLE_NORMAL = (
        "<p style='margin:0; padding:0; font-size:22px; font-weight:700; letter-spacing:0.5px; color:#35D6E7;'>"
        "Secure <span style='color:#FFFFFF;'>Access</span> Point</p>"
        "<p style='margin:4px 0 0 0; padding:0; font-size:12px; color:rgba(53,214,231,0.82); font-weight:400;'>"
        "Enter your credentials to continue securely</p>"
    )
    _TITLE_CHARGING = (
        "<p style='margin:0; padding:0; font-size:22px; font-weight:700; letter-spacing:0.5px; color:#50B4FF;'>"
        "Secure <span style='color:#FFFFFF;'>Access</span> Point</p>"
        "<p style='margin:4px 0 0 0; padding:0; font-size:12px; color:rgba(80,180,255,0.88); font-weight:400;'>"
        "Enter your credentials to continue securely</p>"
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
    title_glow.setBlurRadius(13)
    title_glow.setOffset(0, 0)
    title_glow.setColor(QColor(255, 209, 102, 64))
    title.setGraphicsEffect(title_glow)
    root_layout.addWidget(title)
    root_layout.addSpacing(20)

    card = QFrame()
    card.setObjectName("cardPanel")
    # Shadow utama menggunakan warna border card panel yang lebih kuat
    card_shadow = QGraphicsDropShadowEffect(card)
    card_shadow.setBlurRadius(16)
    card_shadow.setOffset(3, 4)
    card_shadow.setColor(QColor(53, 214, 231, 105))
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
            self._color_normal = QColor(53, 214, 231, 150)
            self._color_normal_core = QColor(53, 214, 231, 230)
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

    username_label = QLabel("User")
    username_label.setObjectName("fieldLabel")
    # Efek glow awal
    username_glow = QGraphicsDropShadowEffect(username_label)
    username_glow.setBlurRadius(7)
    username_glow.setOffset(0, 0)
    username_glow.setColor(QColor(53, 214, 231, 70))
    username_label.setGraphicsEffect(username_glow)
    card_layout.addWidget(username_label)
    card_layout.addSpacing(8)  # Tambahkan jarak 8px antara label dan textbox user

    username_row = QFrame()
    username_row.setObjectName("inputRow")
    username_row.setFixedHeight(41)
    username_layout = QHBoxLayout(username_row)
    username_layout.setContentsMargins(14, 0, 14, 0)
    username_layout.setSpacing(10)

    username_icon = QLabel()
    username_icon.setObjectName("fieldIcon")
    _set_icon(username_icon, _draw_user_icon(18, QColor("#35D6E7")))

    username_input = QLineEdit()
    username_input.setObjectName("fieldInput")
    username_input.setPlaceholderText("Enter your username")

    username_layout.addWidget(username_icon)
    username_layout.addWidget(username_input)
    card_layout.addWidget(username_row)
    # Tambahkan jarak antara input username dan input password
    card_layout.addSpacing(14)

    password_label = QLabel("Password")
    password_label.setObjectName("fieldLabel")
    # Efek glow awal
    password_glow = QGraphicsDropShadowEffect(password_label)
    password_glow.setBlurRadius(7)
    password_glow.setOffset(0, 0)
    password_glow.setColor(QColor(53, 214, 231, 70))
    password_label.setGraphicsEffect(password_glow)
    card_layout.addWidget(password_label)
    card_layout.addSpacing(8)  # Tambahkan jarak 8px antara label dan textbox password

    password_row = QFrame()
    password_row.setObjectName("inputRow")
    password_row.setFixedHeight(41)
    password_layout = QHBoxLayout(password_row)
    password_layout.setContentsMargins(14, 0, 14, 0)
    password_layout.setSpacing(10)

    password_icon = QLabel()
    password_icon.setObjectName("fieldIcon")
    _set_icon(password_icon, _draw_lock_icon(18, QColor("#35D6E7")))

    password_input = QLineEdit()
    password_input.setObjectName("fieldInput")
    password_input.setEchoMode(QLineEdit.EchoMode.Password)
    password_input.setPlaceholderText("Enter your password")

    toggle_password_btn = QToolButton()
    toggle_password_btn.setObjectName("togglePassword")
    toggle_password_btn.setIconSize(QSize(16, 16))
    # Set initial outline color (non-charging)
    # Outline color non-charging disamakan dengan aksen card panel
    # Set ikon awal: crossed=True karena mode Password (karakter disembunyikan)
    # Set ikon awal dengan pupil_color konsisten dengan aksen card panel
    toggle_password_btn.setIcon(QIcon(_draw_eye_icon(16, QColor("#35D6E7"), pupil_color=QColor("#35D6E7"), crossed=True, outline_color=QColor("#35D6E7"))))
    toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    password_layout.addWidget(password_icon)
    password_layout.addWidget(password_input)
    password_layout.addWidget(toggle_password_btn)
    card_layout.addWidget(password_row)
    # Tambahkan jarak antara input password dan status row
    card_layout.addSpacing(22)

    # Divider dihapus sesuai permintaan

    status_row = QHBoxLayout()
    status_row.setSpacing(8)
    status_icon = QLabel()
    status_icon.setObjectName("statusIcon")
    _set_icon(status_icon, _draw_check_icon(19, QColor("#FFFFFF")))
    # Tambahkan efek glow putih pada status_icon agar konsisten dengan status_text
    status_icon_glow = QGraphicsDropShadowEffect(status_icon)
    status_icon_glow.setBlurRadius(12)
    status_icon_glow.setOffset(0, 0)
    status_icon_glow.setColor(QColor(255, 255, 255, 120))
    status_icon.setGraphicsEffect(status_icon_glow)
    status_text = QLabel(f"PIN verified for user: <span style='font-size:15px;'><b>{getattr(pin_user, 'username', '-')}</b></span>")
    status_text.setObjectName("statusText")
    status_text.setTextFormat(Qt.TextFormat.RichText)
    # Efek glow awal
    status_glow = QGraphicsDropShadowEffect(status_text)
    status_glow.setBlurRadius(7)
    status_glow.setOffset(0, 0)
    status_glow.setColor(QColor(53, 214, 231, 70))
    status_text.setGraphicsEffect(status_glow)
    status_row.addWidget(status_icon)
    status_row.addWidget(status_text)
    status_row.addStretch(1)
    card_layout.addLayout(status_row)

    root_layout.addWidget(card)
    root_layout.addSpacing(20)

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
        outline_color = QColor("#50B4FF") if charging else QColor("#35D6E7")
        pupil_color = QColor("#50B4FF") if charging else QColor("#35D6E7")
        crossed = password_input.echoMode() == QLineEdit.EchoMode.Password
        eye_color = QColor("#50B4FF") if charging else QColor("#35D6E7")
        toggle_password_btn.setIcon(QIcon(_draw_eye_icon(16, eye_color, pupil_color=pupil_color, crossed=crossed, outline_color=outline_color)))

    def on_submit() -> None:
        username = username_input.text().strip()
        password = password_input.text()
        if not username or not password:
            _show_credentials_warning(
                dialog,
                "Credentials Required",
                "Enter your username and password.",
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

    # --- Charging state (mengikuti login.py: #50B4FF saat charging) ---
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
            print(f"[DEBUG] credentials charging info: {info}")
        if not info:
            return bool(_charging_cache["prev"])
        charging = info.get("charging")
        if isinstance(charging, bool):
            return charging
        if isinstance(charging, int):
            return bool(charging)
        return bool(_charging_cache["prev"])

    def _apply_charging(charging: bool) -> None:
        dialog.setStyleSheet(_STYLE_CHARGING if charging else _STYLE_NORMAL)
        _refresh_widget_style(dialog)
        title.setText(_TITLE_CHARGING if charging else _TITLE_NORMAL)
        if isinstance(title.graphicsEffect(), QGraphicsDropShadowEffect):
            title_effect = title.graphicsEffect()
            title_effect.setBlurRadius(14 if charging else 13)
            title_effect.setColor(QColor(80, 180, 255, 86) if charging else QColor(255, 209, 102, 64))
        icon_color = QColor("#50B4FF") if charging else QColor("#35D6E7")
        check_color = QColor("#FFFFFF")
        eye_color = QColor("#50B4FF") if charging else QColor("#35D6E7")

        # Update icon colors
        _set_icon(username_icon, _draw_user_icon(18, icon_color))
        _set_icon(password_icon, _draw_lock_icon(18, icon_color))
        _set_icon(status_icon, _draw_check_icon(19, check_color))
        outline_color = QColor("#50B4FF") if charging else QColor("#35D6E7")
        pupil_color = QColor("#50B4FF") if charging else QColor("#35D6E7")
        # Ikuti status visibilitas password
        crossed = password_input.echoMode() == QLineEdit.EchoMode.Password
        toggle_password_btn.setIcon(QIcon(_draw_eye_icon(16, eye_color, pupil_color=pupil_color, crossed=crossed, outline_color=outline_color)))

        # Inline styles must also switch color; otherwise they override the dialog QSS.
        field_label_color = "#FFFFFF"
        status_label_color = "#FFFFFF"
        field_label_style = (
            f"color: {field_label_color}; "
            "font-size: 13px; font-weight: 700; letter-spacing: 0.8px; "
            "font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;"
        )
        username_label.setStyleSheet(field_label_style)  # type: ignore
        password_label.setStyleSheet(field_label_style)  # type: ignore
        status_text.setStyleSheet(
            f"color: {status_label_color}; "
            "font-size: 12px; font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;"
        )  # type: ignore

        # Update glow/outline effect
        glow_color = QColor("#50B4FF" if charging else "#35D6E7")
        glow_alpha = 120 if charging else 70
        for eff in [username_label.graphicsEffect(), password_label.graphicsEffect(), status_text.graphicsEffect()]:
            if isinstance(eff, QGraphicsDropShadowEffect):
                eff.setColor(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), glow_alpha))
                eff.setBlurRadius(12 if charging else 7)

        _apply_action_button_theme(cancel_btn, submit_btn, charging)

        # Update card shadow
        parent_widget = card.parentWidget()
        if charging:
            card_shadow.setBlurRadius(16)
            card_shadow.setOffset(3, 4)
            card_shadow.setColor(QColor(80, 180, 255, 130))
            if parent_widget is not None:
                from PySide6.QtWidgets import QGraphicsEffect
                from typing import cast
                parent_widget.setGraphicsEffect(cast(QGraphicsEffect, None))
        else:
            card_shadow.setBlurRadius(16)
            card_shadow.setOffset(3, 4)
            card_shadow.setColor(QColor(53, 214, 231, 105))
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
            print(f"[DEBUG] credentials charging changed: {_charging_cache['prev']} -> {charging}")
        _charging_cache["prev"] = charging
        _apply_charging(charging)

    _charging_timer = QTimer(dialog)
    _charging_timer.timeout.connect(_update_charging)
    _charging_timer.start(500)
    _update_charging()  # update awal
    # -------------------------------------------------------------------

    username_input.setFocus()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result_user["user"]
    return None
