from datetime import date, datetime
import logging
import secrets
import string
from typing import Optional, TypedDict, cast

from sqlalchemy import text
from PySide6.QtCore import Property, QEvent, QPointF, QRectF, QPropertyAnimation, QEasingCurve, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QEnterEvent,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QLinearGradient,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from database.models import AuditLog, Session, User, UserRole
except ImportError:
    from src.database.models import AuditLog, Session, User, UserRole  # type: ignore[no-redef]

try:
    from database.crud import CANONICAL_ROLES, delete_user, normalize_role_name, set_user_pin, update_user
except ImportError:
    from src.database.crud import CANONICAL_ROLES, delete_user, normalize_role_name, set_user_pin, update_user  # type: ignore[no-redef]

try:
    from auth.passwords import verify_password, verify_pin_code
except ImportError:
    from src.auth.passwords import verify_password, verify_pin_code  # type: ignore[no-redef]

try:
    from app.core.security import verify_password as verify_bcrypt_password
except ImportError:
    verify_bcrypt_password = None  # type: ignore[assignment]

try:
    from ui.credentials_login import _show_credentials_warning
except ImportError:
    from src.ui.credentials_login import _show_credentials_warning  # type: ignore[no-redef]

try:
    from ui.hris_dashboard_data import (
        DEFAULT_REPORTS_DIR,
        HrisQualityIssueRow,
        current_user_has_permission,
        export_hris_quality_issues,
        hris_summary_int,
        is_hris_auth_schema as _is_hris_auth_schema,
        map_hris_role_to_dashboard_role as _map_hris_role_to_dashboard_role,
        read_hris_employee_detail,
        read_hris_employee_id_for_issue,
        read_hris_group_breakdown,
        read_hris_quality_issues,
        read_hris_summary,
        role_names_from_value as _role_names_from_value,
        table_columns as _table_columns,
        table_exists as _table_exists,
        update_hris_quality_issue_statuses,
    )
except ImportError:
    from src.ui.hris_dashboard_data import (  # type: ignore[no-redef]
        DEFAULT_REPORTS_DIR,
        HrisQualityIssueRow,
        current_user_has_permission,
        export_hris_quality_issues,
        hris_summary_int,
        is_hris_auth_schema as _is_hris_auth_schema,
        map_hris_role_to_dashboard_role as _map_hris_role_to_dashboard_role,
        read_hris_employee_detail,
        read_hris_employee_id_for_issue,
        read_hris_group_breakdown,
        read_hris_quality_issues,
        read_hris_summary,
        role_names_from_value as _role_names_from_value,
        table_columns as _table_columns,
        table_exists as _table_exists,
        update_hris_quality_issue_statuses,
    )

_active_dashboard: Optional["DashboardForm"] = None
logger = logging.getLogger(__name__)

NAVY_TOP = "#163A69"
NAVY_SIDE = "#1C467A"
NAVY_SELECTED = "#244F89"
PAGE_BG = "#EFF3F8"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#22324A"
TEXT_SOFT = "#70829A"
DASH_TEXT = "#F4F8FF"
DASH_MUTED = "rgba(230, 237, 246, 0.72)"

TEMP_PASSWORD_LENGTH = 12
CHARGING_ACCENT = "#50B4FF"
CHARGING_MODE_LABEL = "Kondisi Charging"
NOT_CHARGING_MODE_LABEL = "Kondisi Tidak Charging"


class UserRow(TypedDict):
    id: int
    username: str
    full_name: str
    email: str
    phone: str
    role: str
    status: str
    password_value: str
    pin_value: str
    created_at: str
    updated_at: str


def _credential_status_label(is_configured: object) -> str:
    return "Configured" if bool(is_configured) else "Not set"


def _apply_card_shadow(widget: QWidget) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(15, 30, 55, 45))
    widget.setGraphicsEffect(shadow)


def _get_battery_info() -> Optional[dict[str, object]]:
    try:
        from ui.battery_status import get_battery_info
    except ImportError:
        try:
            from src.ui.battery_status import get_battery_info
        except ImportError:
            return None
    return get_battery_info()


def _resolve_charging_state(info: Optional[dict[str, object]]) -> bool:
    if not info:
        return False
    charging = info.get("charging")
    if isinstance(charging, bool):
        return charging
    if isinstance(charging, int):
        return bool(charging)
    return False


def _charging_theme_palette(charging: bool) -> dict[str, str]:
    if charging:
        return {
            "accent": CHARGING_ACCENT,
            "hover": "#3AA8F5",
            "pressed": "#2A96E0",
            "panel_text": "#ECFCFF",
            "panel_muted": "rgba(230, 248, 255, 0.74)",
            "panel_border": "rgba(103, 224, 255, 0.44)",
            "surface_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 55, 76, 0.78), stop:1 rgba(10, 31, 52, 0.70))",
            "surface_hover": "rgba(80, 180, 255, 0.13)",
            "surface_selected": "rgba(80, 180, 255, 0.22)",
            "table_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(20, 44, 65, 0.82), stop:1 rgba(10, 25, 42, 0.78))",
            "table_alt": "rgba(31, 56, 75, 0.72)",
            "table_header": "rgba(33, 68, 94, 0.86)",
            "badge_bg": "rgba(80, 180, 255, 0.14)",
            "badge_border": "rgba(80, 180, 255, 0.34)",
            "badge_text": CHARGING_ACCENT,
            "badge_label": CHARGING_MODE_LABEL,
        }
    return {
        "accent": "#FFFFFF",
        "hover": "#DDE6F2",
        "pressed": "#AEBBCC",
        "panel_text": "#F4F8FF",
        "panel_muted": "rgba(230, 237, 246, 0.72)",
        "panel_border": "rgba(255, 255, 255, 0.26)",
        "surface_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(38, 47, 59, 0.76), stop:1 rgba(19, 28, 40, 0.70))",
        "surface_hover": "rgba(255, 255, 255, 0.09)",
        "surface_selected": "rgba(255, 255, 255, 0.16)",
        "table_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(32, 41, 53, 0.82), stop:1 rgba(17, 25, 36, 0.78))",
        "table_alt": "rgba(38, 47, 59, 0.72)",
        "table_header": "rgba(43, 52, 65, 0.86)",
        "badge_bg": "rgba(255, 255, 255, 0.10)",
        "badge_border": "rgba(255, 255, 255, 0.24)",
        "badge_text": "#F4F8FF",
        "badge_label": NOT_CHARGING_MODE_LABEL,
    }


def _paint_login_reference_surface(
    painter: QPainter,
    event: QPaintEvent,
    width: int,
    height: int,
    corner_radius: float,
    charging: bool,
    *,
    focus_y: float = 42.0,
    focus_radius: float = 178.0,
    fill_transparent: bool = True,
) -> None:
    """Paint the same layered glass surface language used by LoginDialog in login.py."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if fill_transparent:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    border_inset = 1.0
    rect = QRectF(border_inset, border_inset, width - (border_inset * 2.0), height - (border_inset * 2.0))
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
    inner_pen = QPen(inner_border_color, 0.65)
    inner_pen.setCosmetic(True)
    painter.setPen(inner_pen)
    painter.drawRoundedRect(rect.adjusted(1.05, 1.05, -1.05, -1.05), radius - 1.05, radius - 1.05)
    border_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    border_gradient.setColorAt(0.0, border_top_color)
    border_gradient.setColorAt(0.46, border_color)
    border_gradient.setColorAt(1.0, border_bottom_color)
    border_pen = QPen(QBrush(border_gradient), 1.0)
    border_pen.setCosmetic(True)
    painter.setPen(border_pen)
    painter.drawRoundedRect(rect, radius, radius)


class LoginGlassPanel(QFrame):
    def __init__(self, radius: float = 18.0, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._charging = False
        self._radius = radius
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
        _paint_login_reference_surface(
            painter,
            event,
            self.width(),
            self.height(),
            self._radius,
            self._charging,
            focus_y=max(28.0, min(86.0, self.height() * 0.36)),
            focus_radius=max(120.0, self.width() * 0.28),
        )
        painter.end()


class DashboardBackground(QWidget):
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
        _paint_login_reference_surface(
            painter,
            event,
            self.width(),
            self.height(),
            5.0,
            self._charging,
            focus_y=96.0,
            focus_radius=max(260.0, self.width() * 0.34),
        )
        painter.end()


def _read_charging_state_from_context(parent: Optional[QWidget], fallback: bool = False) -> bool:
    widget = parent
    while widget is not None:
        value = getattr(widget, "_charging", None)
        if isinstance(value, bool):
            return value
        widget = widget.parentWidget()

    info = _get_battery_info()
    if info is None:
        return fallback
    return _resolve_charging_state(info)


def _dashboard_dialog_stylesheet(charging: bool) -> str:
    palette = _charging_theme_palette(charging)
    focus_border = "rgba(103, 224, 255, 0.54)" if charging else "rgba(255, 255, 255, 0.42)"
    return (
        "QDialog { background: transparent; }"
        f"QLabel {{ color: {palette['panel_text']}; background: transparent; }}"
        "QLineEdit, QComboBox {"
        f" background: {palette['surface_bg']};"
        f" color: {palette['panel_text']};"
        f" border: 1px solid {palette['panel_border']};"
        " border-radius: 9px; padding: 0 11px; font-size: 13px; font-weight: 650;"
        " selection-background-color: rgba(80, 180, 255, 0.35);"
        "}"
        f"QLineEdit:focus, QComboBox:focus {{ border: 1px solid {focus_border}; }}"
        "QLineEdit::placeholder { color: rgba(230, 237, 246, 0.46); }"
        "QComboBox::drop-down { border: none; width: 24px; }"
        "QDialogButtonBox QPushButton {"
        f" background: {palette['surface_selected']}; color: {palette['panel_text']};"
        f" border: 1px solid {palette['panel_border']};"
        " border-radius: 8px; padding: 7px 18px; font-size: 13px; font-weight: 800;"
        "}"
        f"QDialogButtonBox QPushButton:hover {{ background: {palette['surface_hover']}; }}"
        f"QDialogButtonBox QPushButton:pressed {{ background: {palette['surface_selected']}; }}"
    )


class DashboardGlassDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, radius: float = 18.0) -> None:
        super().__init__(parent)
        self._charging: Optional[bool] = None
        self._background_radius = radius
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
        _paint_login_reference_surface(
            painter,
            event,
            self.width(),
            self.height(),
            self._background_radius,
            bool(self._charging),
            focus_y=max(36.0, min(92.0, self.height() * 0.24)),
            focus_radius=max(150.0, self.width() * 0.48),
        )
        painter.end()


class InfoCard(QFrame):
    def __init__(self, icon: str, title: str, value: str, value_color: str) -> None:
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )
        self.setMinimumHeight(120)
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 28px;")
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 13px; font-weight: 700;")
        top.addWidget(icon_label)
        top.addWidget(title_label)
        top.addStretch()

        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {value_color}; font-size: 24px; font-weight: 800;")

        layout.addLayout(top)
        layout.addWidget(value_label)
        layout.addStretch()


class SectionCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 14px; font-weight: 800;")
        layout.addWidget(title_label)
        self.body_layout = layout


class AnimatedNavItem(QLabel):
    clicked = Signal(str)

    def __init__(self, text: str, active: bool = False, item_key: Optional[str] = None) -> None:
        super().__init__(text)
        self._active = active
        self._item_key = item_key or text
        self._charging = False
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress")
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._press_anim = QPropertyAnimation(self, b"pressProgress")
        self._press_anim.setDuration(110)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setFixedHeight(38)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def _animate_hover(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _apply_style(self) -> None:
        depth = (self._hover_progress * 8.0) - (self._press_progress * 5.0)
        palette = _charging_theme_palette(self._charging)
        text_color = palette["panel_text"]
        border_color = palette["accent"]
        if self._active:
            pad = 18 + int(depth)
            self.setStyleSheet(
                f"background: {palette['surface_selected']}; color: {text_color}; font-size: 14px; font-weight: 800;"
                f"border-left: 4px solid {border_color}; padding-left: {pad}px;"
            )
            return

        alpha = int((70 * self._hover_progress) + (35 * self._press_progress))
        pad = 22 + int(depth)
        self.setStyleSheet(
            f"color: {text_color}; font-size: 14px; font-weight: 600;"
            f"background: rgba(255, 255, 255, {alpha});"
            f"padding-left: {pad}px;"
        )

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = float(value)
        self._apply_style()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def _animate_press(self, target: float) -> None:
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(target)
        self._press_anim.start()

    def get_press_progress(self) -> float:
        return self._press_progress

    def set_press_progress(self, value: float) -> None:
        self._press_progress = float(value)
        self._apply_style()

    pressProgress = Property(float, get_press_progress, set_press_progress)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._animate_press(1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._animate_press(0.0)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._item_key)
        super().mouseReleaseEvent(event)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_style()

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self._apply_style()


class AnimatedHoverCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self._hover_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress")
        self._hover_anim.setDuration(180)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(18)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(15, 30, 55, 45))
        self.setGraphicsEffect(self._shadow)

    def _animate_hover(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = float(value)
        blur = 18 + (10 * self._hover_progress)
        offset = 4 + (3 * self._hover_progress)
        alpha = 45 + int(30 * self._hover_progress)
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(0, offset)
        self._shadow.setColor(QColor(15, 30, 55, alpha))

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)


class AnimatedInfoCard(AnimatedHoverCard):
    def __init__(self, icon: str, title: str, value: str, value_color: str) -> None:
        super().__init__()
        self._charging = False
        self._value_color = value_color
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet("font-size: 28px; background: transparent;")
        self._title_label = QLabel(title)
        top.addWidget(self._icon_label)
        top.addWidget(self._title_label)
        top.addStretch()

        self._value_label = QLabel(value)

        layout.addLayout(top)
        layout.addWidget(self._value_label)
        layout.addStretch()
        self._apply_text_style()

    def _apply_text_style(self) -> None:
        palette = _charging_theme_palette(self._charging)
        self._title_label.setStyleSheet(
            f"color: {palette['panel_muted']}; font-size: 13px; font-weight: 700; background: transparent;"
        )
        value_color = palette["accent"] if self._value_color in {"#1D4ED8"} else self._value_color
        self._value_label.setStyleSheet(
            f"color: {value_color}; font-size: 24px; font-weight: 800; background: transparent;"
        )

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self._apply_text_style()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        _paint_login_reference_surface(
            painter,
            event,
            self.width(),
            self.height(),
            16.0,
            self._charging,
            focus_y=34.0,
            focus_radius=max(130.0, self.width() * 0.52),
        )
        painter.end()


class AnimatedSectionCard(AnimatedHoverCard):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._charging = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        self._title_label = QLabel(title)
        layout.addWidget(self._title_label)
        self.body_layout = layout
        self._apply_text_style()

    def _apply_text_style(self) -> None:
        palette = _charging_theme_palette(self._charging)
        self._title_label.setStyleSheet(
            f"color: {palette['panel_text']}; font-size: 14px; font-weight: 800; background: transparent;"
        )

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self._apply_text_style()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        _paint_login_reference_surface(
            painter,
            event,
            self.width(),
            self.height(),
            16.0,
            self._charging,
            focus_y=42.0,
            focus_radius=max(150.0, self.width() * 0.42),
        )
        painter.end()


class AnimatedActionButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._charging = False

        self._hover_anim = QPropertyAnimation(self, b"hoverProgress")
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_anim = QPropertyAnimation(self, b"pressProgress")
        self._press_anim.setDuration(100)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(16)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(QColor(120, 35, 25, 120))
        self.setGraphicsEffect(self._shadow)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")
        self._apply_style()

    def _apply_style(self) -> None:
        blur = 16 + (8 * self._hover_progress)
        offset = 3 + (2 * self._hover_progress)
        alpha = 120 + int(45 * self._hover_progress)
        shadow_color = QColor(80, 180, 255, alpha) if self._charging else QColor(0, 0, 0, max(42, alpha // 2))
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(0, offset)
        self._shadow.setColor(shadow_color)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _animate_press(self, target: float) -> None:
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(target)
        self._press_anim.start()

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = float(value)
        self._apply_style()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def get_press_progress(self) -> float:
        return self._press_progress

    def set_press_progress(self, value: float) -> None:
        self._press_progress = float(value)
        self._apply_style()

    pressProgress = Property(float, get_press_progress, set_press_progress)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_hover(0.0)
        self._animate_press(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._animate_press(1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._animate_press(0.0)
        super().mouseReleaseEvent(event)

    def set_charging(self, charging: bool) -> None:
        charging = bool(charging)
        if self._charging == charging:
            return
        self._charging = charging
        self._apply_style()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        lift = 0.8 if self._press_progress > 0.01 else 0.0
        rect = QRectF(2.0, 2.0 + lift, self.width() - 4.0, self.height() - 4.0)
        radius = min(14.0, rect.height() * 0.34)
        hovered = self._hover_progress > 0.01

        if self._charging:
            center_color = QColor(34, 72, 96, 218)
            mid_color = QColor(16, 49, 74, 224)
            edge_color = QColor(5, 27, 49, 235)
            bevel_top = QColor(188, 244, 255, 58)
            bevel_bottom = QColor(1, 13, 28, 112)
            border_top = QColor(188, 244, 255, 82)
            border_bottom = QColor(40, 124, 210, 42)
            halo_color = QColor(80, 180, 255, 18)
            text_top = QColor(236, 252, 255)
            text_bottom = QColor(91, 198, 255)
        else:
            center_color = QColor(65, 74, 88, 218)
            mid_color = QColor(39, 48, 61, 224)
            edge_color = QColor(17, 26, 39, 235)
            bevel_top = QColor(255, 255, 255, 48)
            bevel_bottom = QColor(0, 0, 0, 108)
            border_top = QColor(255, 255, 255, 68)
            border_bottom = QColor(182, 194, 210, 28)
            halo_color = QColor(255, 255, 255, 12)
            text_top = QColor(255, 255, 255)
            text_bottom = QColor(211, 222, 236)

        if hovered:
            center_color.setAlpha(min(255, center_color.alpha() + 16))
            mid_color.setAlpha(min(255, mid_color.alpha() + 18))
            border_top.setAlpha(min(255, border_top.alpha() + 18))
            halo_color.setAlpha(min(255, halo_color.alpha() + 10))

        painter.setPen(Qt.PenStyle.NoPen)
        halo = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.74)
        halo.setColorAt(0.0, halo_color)
        halo.setColorAt(0.84, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), max(2, halo_color.alpha() // 3)))
        halo.setColorAt(1.0, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), 0))
        painter.setBrush(QBrush(halo))
        painter.drawRoundedRect(rect.adjusted(-1.0, -1.0, 1.0, 1.0), radius + 1.0, radius + 1.0)

        base = QRadialGradient(rect.center() + QPointF(-rect.width() * 0.16, -rect.height() * 0.25), rect.width() * 0.78)
        base.setColorAt(0.0, center_color)
        base.setColorAt(0.58, mid_color)
        base.setColorAt(1.0, edge_color)
        painter.setBrush(QBrush(base))
        painter.drawRoundedRect(rect, radius, radius)

        bevel = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        bevel.setColorAt(0.0, bevel_top)
        bevel.setColorAt(0.34, QColor(bevel_top.red(), bevel_top.green(), bevel_top.blue(), 0))
        bevel.setColorAt(0.72, QColor(bevel_bottom.red(), bevel_bottom.green(), bevel_bottom.blue(), 0))
        bevel.setColorAt(1.0, bevel_bottom)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(bevel), 1.1))
        painter.drawRoundedRect(rect.adjusted(1.0, 1.0, -1.0, -1.0), radius - 1.0, radius - 1.0)

        border = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        border.setColorAt(0.0, border_top)
        border.setColorAt(1.0, border_bottom)
        border_pen = QPen(QBrush(border), 0.9)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, radius, radius)

        font = QFont("Segoe UI")
        font.setPointSizeF(9.6)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text = self.text()
        text_rect = self.rect().adjusted(8, 0, -8, 0)
        x = text_rect.left() + (text_rect.width() - metrics.horizontalAdvance(text)) / 2
        y = text_rect.top() + (text_rect.height() + metrics.ascent() - metrics.descent()) / 2 + lift
        text_path = QPainterPath()
        text_path.addText(QPointF(x, y), font, text)
        bounds = text_path.boundingRect()
        shadow_path = QPainterPath(text_path)
        shadow_path.translate(0.0, 1.1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 118 if self._charging else 96)))
        painter.drawPath(shadow_path)
        text_grad = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.bottom())
        text_grad.setColorAt(0.0, text_top)
        text_grad.setColorAt(1.0, text_bottom)
        painter.setBrush(QBrush(text_grad))
        painter.drawPath(text_path)
        painter.end()


class ChangePasswordDialog(DashboardGlassDialog):
    """Dialog untuk mengganti password dan PIN user sendiri"""

    def __init__(self, username: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, radius=18.0)
        self.setWindowTitle("Ganti Password")
        self.setModal(True)
        self.resize(420, 280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setSpacing(10)

        self._title = QLabel(f"Ganti Password dan PIN\nUser: {username}")
        layout.addWidget(self._title)

        self._old_password_input = QLineEdit()
        self._old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_password_input.setFixedHeight(36)
        self._old_password_input.setPlaceholderText("Masukkan password lama")

        self._new_password_input = QLineEdit()
        self._new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_password_input.setFixedHeight(36)
        self._new_password_input.setPlaceholderText("Masukkan password baru")

        self._old_pin_input = QLineEdit()
        self._old_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_pin_input.setFixedHeight(36)
        self._old_pin_input.setPlaceholderText("Masukkan PIN lama (6 digit)")
        self._old_pin_input.setMaxLength(6)

        self._new_pin_input = QLineEdit()
        self._new_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pin_input.setFixedHeight(36)
        self._new_pin_input.setPlaceholderText("Masukkan PIN baru (6 digit)")
        self._new_pin_input.setMaxLength(6)

        form.addRow("Password Lama", self._old_password_input)
        form.addRow("Password Baru", self._new_password_input)
        form.addRow("PIN Lama", self._old_pin_input)
        form.addRow("PIN Baru", self._new_pin_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._buttons = buttons

        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._update_charging_theme)
        self._charging_timer.start(500)
        self._update_charging_theme()

    def _update_charging_theme(self) -> None:
        charging = _read_charging_state_from_context(self.parentWidget(), bool(self._charging))
        if self._charging == charging and self.styleSheet():
            return
        self.set_charging(charging)
        palette = _charging_theme_palette(charging)
        self.setStyleSheet(_dashboard_dialog_stylesheet(charging))
        self._title.setStyleSheet(
            f"color: {palette['panel_text']}; font-size: 15px; font-weight: 850; background: transparent;"
        )

    def data(self) -> dict[str, str]:
        return {
            "old_password": self._old_password_input.text(),
            "new_password": self._new_password_input.text(),
            "old_pin": self._old_pin_input.text().strip(),
            "new_pin": self._new_pin_input.text().strip(),
        }


class UserEditDialog(DashboardGlassDialog):
    def __init__(
        self,
        username: str,
        nama: str,
        role: str,
        status: str,
        current_password: str = "",
        current_pin: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent, radius=18.0)
        self.setWindowTitle("Edit User")
        self.setModal(True)
        self.resize(520, 660)
        self._edit_glass_panels: list[LoginGlassPanel] = []
        self._edit_row_labels: list[QLabel] = []
        self._edit_hint_labels: list[QLabel] = []
        self._edit_fields: list[QLineEdit] = []
        self._edit_combos: list[QComboBox] = []
        self._edit_theme_applied = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # --- Accent bar ---
        self._header_bar = QFrame()
        self._header_bar.setFixedHeight(4)
        self._header_bar.setStyleSheet(f"background: {NAVY_TOP}; border-radius: 2px;")
        main_layout.addWidget(self._header_bar)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        header_block = QVBoxLayout()
        header_block.setContentsMargins(0, 0, 0, 0)
        header_block.setSpacing(4)

        self._header_label = QLabel("Edit User")
        self._header_subtitle = QLabel(
            "Manage profile details, access status, and credential reset in one panel."
        )
        self._header_subtitle.setWordWrap(True)
        header_block.addWidget(self._header_label)
        header_block.addWidget(self._header_subtitle)

        self._theme_badge = QLabel(NOT_CHARGING_MODE_LABEL)
        self._theme_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._theme_badge.setMinimumWidth(158)
        self._theme_badge.setFixedHeight(30)

        header_row.addLayout(header_block, 1)
        header_row.addWidget(self._theme_badge, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(header_row)

        # --- Section: User Information ---
        info_card = LoginGlassPanel(12.0)
        self._edit_glass_panels.append(info_card)
        info_card.setStyleSheet("background: transparent;")
        _apply_card_shadow(info_card)
        info_inner = QVBoxLayout(info_card)
        info_inner.setContentsMargins(20, 14, 20, 14)
        info_inner.setSpacing(10)

        self._info_title = QLabel("User Information")
        self._info_title.setStyleSheet(
            f"color: {NAVY_TOP}; font-size: 12px; font-weight: 800;"
            " border: none; background: transparent;"
        )
        info_inner.addWidget(self._info_title)

        info_form = QFormLayout()
        info_form.setSpacing(8)
        self._username_input = self._make_field(username)
        self._nama_input = self._make_field(nama)
        self._role_combo = QComboBox()
        self._role_combo.addItems(list(CANONICAL_ROLES))
        self._role_combo.setFixedHeight(36)
        self._role_combo.setStyleSheet(self._combo_style())
        self._edit_combos.append(self._role_combo)
        try:
            normalized_role = normalize_role_name(role)
        except ValueError:
            normalized_role = "Operator"
        self._role_combo.setCurrentText(normalized_role)
        self._status_combo = QComboBox()
        self._status_combo.addItems(["Active", "Inactive"])
        self._status_combo.setFixedHeight(36)
        self._status_combo.setStyleSheet(self._combo_style())
        self._edit_combos.append(self._status_combo)
        normalized_status = status.strip().lower()
        self._status_combo.setCurrentText(
            "Active" if normalized_status in {"aktif", "active"} else "Inactive"
        )
        info_form.addRow(self._row_label("Username"), self._username_input)
        info_form.addRow(self._row_label("Full Name"), self._nama_input)
        info_form.addRow(self._row_label("Role"), self._role_combo)
        info_form.addRow(self._row_label("Status"), self._status_combo)
        info_inner.addLayout(info_form)
        main_layout.addWidget(info_card)

        # --- Section: Credential Reset ---
        old_card = LoginGlassPanel(12.0)
        self._edit_glass_panels.append(old_card)
        old_card.setStyleSheet("background: transparent;")
        _apply_card_shadow(old_card)
        old_inner = QVBoxLayout(old_card)
        old_inner.setContentsMargins(20, 14, 20, 14)
        old_inner.setSpacing(10)

        self._old_title = QLabel("Credential Reset")
        self._old_title.setStyleSheet(
            f"color: {NAVY_TOP}; font-size: 12px; font-weight: 800;"
            " border: none; background: transparent;"
        )
        old_inner.addWidget(self._old_title)

        old_form = QFormLayout()
        old_form.setSpacing(8)
        self._old_password_input = self._make_field()
        self._old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_password_input.setPlaceholderText("Optional current password verification")
        self._old_pin_input = self._make_field()
        self._old_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_pin_input.setPlaceholderText("Optional current PIN verification")
        self._old_pin_input.setMaxLength(6)
        old_form.addRow(self._row_label("Verify Password"), self._old_password_input)
        old_form.addRow(self._row_label("Verify PIN"), self._old_pin_input)
        old_inner.addLayout(old_form)
        old_hint = QLabel("Stored credentials are never displayed. Use verification only when needed.")
        old_hint.setWordWrap(True)
        self._edit_hint_labels.append(old_hint)
        old_inner.addWidget(old_hint)
        main_layout.addWidget(old_card)

        # --- Section: New Credentials ---
        new_card = LoginGlassPanel(12.0)
        self._edit_glass_panels.append(new_card)
        new_card.setStyleSheet("background: transparent;")
        _apply_card_shadow(new_card)
        new_inner = QVBoxLayout(new_card)
        new_inner.setContentsMargins(20, 14, 20, 14)
        new_inner.setSpacing(10)

        self._new_title = QLabel("New Credentials")
        self._new_title.setStyleSheet(
            f"color: {NAVY_TOP}; font-size: 12px; font-weight: 800;"
            " border: none; background: transparent;"
        )
        new_inner.addWidget(self._new_title)

        new_form = QFormLayout()
        new_form.setSpacing(8)
        self._new_password_input = self._make_field()
        self._new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_password_input.setPlaceholderText("New password (leave blank to keep current)")
        self._new_pin_input = self._make_field()
        self._new_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pin_input.setPlaceholderText("New 6-digit PIN (leave blank to keep current)")
        self._new_pin_input.setMaxLength(6)
        new_form.addRow(self._row_label("New Password"), self._new_password_input)
        new_form.addRow(self._row_label("New PIN"), self._new_pin_input)
        new_inner.addLayout(new_form)
        new_hint = QLabel("Leave new fields blank if no credential update is needed.")
        new_hint.setWordWrap(True)
        self._edit_hint_labels.append(new_hint)
        new_inner.addWidget(new_hint)
        main_layout.addWidget(new_card)

        main_layout.addStretch()

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setFixedHeight(40)
        self._btn_cancel.setMinimumWidth(100)
        self._btn_cancel.clicked.connect(self.reject)

        self._btn_save = QPushButton("Save Changes")
        self._btn_save.setFixedHeight(40)
        self._btn_save.setMinimumWidth(140)
        self._btn_save.clicked.connect(self.accept)

        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_save)
        main_layout.addLayout(btn_row)

        # --- Battery-aware color polling ---
        self._battery_timer = QTimer(self)
        self._battery_timer.timeout.connect(self._update_charging_theme)
        self._battery_timer.start(3000)
        self._update_charging_theme()

    def _row_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        self._edit_row_labels.append(lbl)
        lbl.setStyleSheet(self._row_label_style())
        return lbl

    def _make_field(self, text: str = "") -> QLineEdit:
        inp = QLineEdit(text)
        inp.setFixedHeight(36)
        self._edit_fields.append(inp)
        inp.setStyleSheet(self._field_style())
        return inp

    def _combo_style(self) -> str:
        return self._field_style(widget_type="QComboBox")

    def _field_style(self, widget_type: str = "QLineEdit") -> str:
        palette = _charging_theme_palette(bool(self._charging))
        focus_border = "rgba(103, 224, 255, 0.54)" if bool(self._charging) else "rgba(255, 255, 255, 0.42)"
        return f"""
            {widget_type} {{
                background: {palette['surface_bg']};
                border: 1px solid {palette['panel_border']};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 13px;
                font-weight: 650;
                color: {palette['panel_text']};
                selection-background-color: rgba(80, 180, 255, 0.35);
            }}
            {widget_type}:focus {{
                border: 1px solid {focus_border};
            }}
            QLineEdit::placeholder {{
                color: rgba(230, 237, 246, 0.46);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """

    def _row_label_style(self) -> str:
        palette = _charging_theme_palette(bool(self._charging))
        return (
            f"color: {palette['panel_muted']}; font-size: 12px; font-weight: 650;"
            " border: none; background: transparent;"
        )

    def _cancel_btn_style(self, charging: bool) -> str:
        palette = _charging_theme_palette(charging)
        return f"""
            QPushButton {{
                background: {palette['surface_bg']};
                color: {palette['panel_text']};
                border: 1px solid {palette['panel_border']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 750;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: {palette['surface_hover']}; }}
            QPushButton:pressed {{ background: {palette['surface_selected']}; }}
        """

    def _save_btn_style(self, charging: bool) -> str:
        if charging:
            bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(34, 72, 96, 0.98), stop:1 rgba(18, 65, 88, 0.98))"
            hover = "rgba(80, 180, 255, 0.30)"
            pressed = "rgba(80, 180, 255, 0.20)"
            border = "rgba(103, 224, 255, 0.55)"
            text = "#ECFCFF"
        else:
            bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(65, 74, 88, 0.92), stop:1 rgba(27, 36, 49, 0.92))"
            hover = "rgba(255, 255, 255, 0.18)"
            pressed = "rgba(255, 255, 255, 0.12)"
            border = "rgba(255, 255, 255, 0.30)"
            text = "#FFFFFF"
        return f"""
            QPushButton {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 800;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:pressed {{ background: {pressed}; }}
        """

    def _badge_style(self, bg: str, border: str, text: str) -> str:
        return f"""
            QLabel {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 15px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 10px;
            }}
        """

    def _update_charging_theme(self) -> None:
        charging = _read_charging_state_from_context(self.parentWidget(), bool(self._charging))
        if charging == self._charging and self._edit_theme_applied:
            return
        self.set_charging(charging)
        self._edit_theme_applied = True
        palette = _charging_theme_palette(charging)
        accent = palette["accent"]
        self.setStyleSheet(_dashboard_dialog_stylesheet(charging))
        self._header_bar.setStyleSheet(
            f"background: {accent}; border-radius: 2px;"
        )
        for panel in self._edit_glass_panels:
            panel.set_charging(charging)
        self._header_label.setStyleSheet(
            f"color: {palette['panel_text']}; font-size: 18px; font-weight: 900; background: transparent;"
        )
        self._header_subtitle.setStyleSheet(
            f"color: {palette['panel_muted']}; font-size: 12px; font-weight: 600; background: transparent;"
        )
        title_css = (
            f"color: {accent}; font-size: 12px; font-weight: 800;"
            " border: none; background: transparent;"
        )
        self._info_title.setStyleSheet(title_css)
        self._old_title.setStyleSheet(title_css)
        self._new_title.setStyleSheet(title_css)
        for label in self._edit_row_labels:
            label.setStyleSheet(self._row_label_style())
        for label in self._edit_hint_labels:
            label.setStyleSheet(
                f"color: {palette['panel_muted']}; font-size: 11px; font-weight: 600; background: transparent;"
            )
        for field in self._edit_fields:
            field.setStyleSheet(self._field_style())
        for combo in self._edit_combos:
            combo.setStyleSheet(self._combo_style())
        self._theme_badge.setText(palette["badge_label"])
        self._theme_badge.setStyleSheet(
            self._badge_style(
                palette["badge_bg"],
                palette["badge_border"],
                palette["badge_text"],
            )
        )
        self._btn_cancel.setStyleSheet(self._cancel_btn_style(charging))
        self._btn_save.setStyleSheet(self._save_btn_style(charging))

    def data(self) -> dict[str, str]:
        selected_status = self._status_combo.currentText().strip().lower()
        normalized_status = "aktif" if selected_status == "active" else "nonaktif"
        return {
            "username": self._username_input.text().strip(),
            "nama": self._nama_input.text().strip(),
            "role": self._role_combo.currentText().strip().lower(),
            "status": normalized_status,
            "old_password": self._old_password_input.text(),
            "new_password": self._new_password_input.text(),
            "old_pin": self._old_pin_input.text().strip(),
            "new_pin": self._new_pin_input.text().strip(),
        }


class UserAddDialog(DashboardGlassDialog):
    """Dialog to add a new user (password and PIN are auto-generated)."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, radius=18.0)
        self.setWindowTitle("Add User")
        self.setModal(True)
        self.resize(420, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setSpacing(10)

        self._username_input = QLineEdit()
        self._username_input.setFixedHeight(36)
        self._username_input.setPlaceholderText("Example: riko01")
        
        self._nama_input = QLineEdit()
        self._nama_input.setFixedHeight(36)
        self._nama_input.setPlaceholderText("Example: Riko Sinaga")
        
        self._role_combo = QComboBox()
        self._role_combo.addItems(list(CANONICAL_ROLES))
        self._role_combo.setFixedHeight(36)
        self._role_combo.setCurrentText("Operator")
        
        self._status_combo = QComboBox()
        self._status_combo.addItems(["Active", "Inactive"])
        self._status_combo.setFixedHeight(36)

        form.addRow("Username", self._username_input)
        form.addRow("Full Name", self._nama_input)
        form.addRow("Role", self._role_combo)
        form.addRow("Status", self._status_combo)
        layout.addLayout(form)
        
        self._info_label = QLabel("Password and PIN will be generated automatically.")
        layout.addWidget(self._info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._buttons = buttons

        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._update_charging_theme)
        self._charging_timer.start(500)
        self._update_charging_theme()

    def _update_charging_theme(self) -> None:
        charging = _read_charging_state_from_context(self.parentWidget(), bool(self._charging))
        if self._charging == charging and self.styleSheet():
            return
        self.set_charging(charging)
        palette = _charging_theme_palette(charging)
        self.setStyleSheet(_dashboard_dialog_stylesheet(charging))
        self._info_label.setStyleSheet(
            f"color: {palette['panel_muted']}; font-size: 12px; font-style: italic; font-weight: 650; background: transparent;"
        )

    def data(self) -> dict[str, str]:
        selected_status = self._status_combo.currentText().strip().lower()
        normalized_status = "aktif" if selected_status == "active" else "nonaktif"
        return {
            "username": self._username_input.text().strip(),
            "nama": self._nama_input.text().strip(),
            "password": "",  # Will be auto-generated
            "role": self._role_combo.currentText().strip().lower(),
            "status": normalized_status,
        }


class DashboardForm(QMainWindow):
    def __init__(self, user: Optional[User] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user
        self._charging: Optional[bool] = None
        self._nav_items: dict[str, AnimatedNavItem] = {}
        self._glass_panels: list[LoginGlassPanel] = []
        self._info_cards: list[AnimatedInfoCard] = []
        self._section_cards: list[AnimatedSectionCard] = []
        self._action_buttons: list[AnimatedActionButton] = []
        self._dashboard_text_labels: list[QLabel] = []
        self._dashboard_muted_labels: list[QLabel] = []
        self._dashboard_badges: list[QLabel] = []
        self._page_title_labels: list[QLabel] = []
        self._chart_area: Optional[QFrame] = None
        self._footer_label: Optional[QLabel] = None
        self._page_title_label: Optional[QLabel] = None
        self._add_user_btn: Optional[QPushButton] = None
        self._header_title: Optional[QLabel] = None
        self._header_brand: Optional[QLabel] = None
        self._header_user_info: Optional[QLabel] = None
        self._header_mode_badge: Optional[QLabel] = None
        self._users_table: Optional[QTableWidget] = None
        self._hris_quality_table: Optional[QTableWidget] = None
        self._hris_quality_refresh_btn: Optional[QPushButton] = None
        self._hris_quality_verify_selected_btn: Optional[QPushButton] = None
        self._hris_quality_ignore_selected_btn: Optional[QPushButton] = None
        self._hris_quality_fixed_selected_btn: Optional[QPushButton] = None
        self._hris_quality_export_btn: Optional[QPushButton] = None
        self._hris_quality_action_buttons: list[QPushButton] = []
        self._hris_quality_search: Optional[QLineEdit] = None
        self._hris_quality_status_filter: Optional[QComboBox] = None
        self._hris_quality_severity_filter: Optional[QComboBox] = None
        self._hris_quality_summary_label: Optional[QLabel] = None
        self._search_username: Optional[QLineEdit] = None
        self._role_filter: Optional[QComboBox] = None
        self._all_users_rows: list[UserRow] = []
        self.setWindowTitle("Dashboard")
        self.resize(1360, 820)
        self.setMinimumSize(960, 600)

        root = DashboardBackground(self)
        self._root_background = root
        root.setStyleSheet("background: transparent;")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)
        content_row.addWidget(self._build_sidebar())
        content_row.addWidget(self._build_content_stack(), 1)

        body = QWidget()
        body.setLayout(content_row)
        root_layout.addWidget(body, 1)
        root_layout.addWidget(self._build_footer())

        self.setCentralWidget(root)
        self._charging_timer = QTimer(self)
        self._charging_timer.timeout.connect(self._update_charging_theme)
        self._charging_timer.start(200)
        self._update_charging_theme()

    def current_user_id(self) -> int:
        return int(getattr(self._user, "id", 0) or 0)

    def _build_temp_password(self, length: int = TEMP_PASSWORD_LENGTH) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _build_content_stack(self) -> QWidget:
        self._content_stack = QStackedWidget()
        self._dashboard_overview_page = self._build_content()
        self._hris_manpower_page = self._build_hris_manpower_page()
        self._management_user_page = self._build_management_users_page()
        self._content_stack.addWidget(self._dashboard_overview_page)
        self._content_stack.addWidget(self._hris_manpower_page)
        self._content_stack.addWidget(self._management_user_page)
        self._content_stack.setCurrentWidget(self._dashboard_overview_page)
        return self._content_stack

    def _build_header(self) -> QWidget:
        header = LoginGlassPanel(5.0)
        self._glass_panels.append(header)
        header.setFixedHeight(88)
        header.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 10, 22, 10)
        layout.setSpacing(16)

        self._header_brand = QLabel("🌴  SISTEM KEBUN SAWIT")

        self._header_title = QLabel("Dashboard Utama")
        self._header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        username = self._user.username if self._user is not None else "User"
        raw_role = str(getattr(self._user, "role", "Operator") or "Operator") if self._user is not None else "Operator"
        try:
            role = normalize_role_name(raw_role)
        except ValueError:
            role = raw_role
        date_text = date.today().strftime("%d %B %Y")
        self._header_user_info = QLabel(f"User: {username}  |  Level: {role}\nTanggal: {date_text}")
        self._header_user_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._header_mode_badge = QLabel(NOT_CHARGING_MODE_LABEL)
        self._header_mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_mode_badge.setFixedSize(166, 32)

        change_password_btn = AnimatedActionButton("Ganti Password")
        change_password_btn.setFixedSize(140, 40)
        change_password_btn.clicked.connect(self._open_change_password_dialog)
        self._action_buttons.append(change_password_btn)

        logout_btn = AnimatedActionButton("Logout")
        logout_btn.setFixedSize(108, 40)
        logout_btn.clicked.connect(self.close)
        self._action_buttons.append(logout_btn)

        layout.addWidget(self._header_brand)
        layout.addStretch(1)
        layout.addWidget(self._header_title)
        layout.addStretch(1)
        layout.addWidget(self._header_user_info)
        layout.addWidget(self._header_mode_badge)
        layout.addWidget(change_password_btn)
        layout.addWidget(logout_btn)
        return header

    def _build_sidebar(self) -> QWidget:
        sidebar = LoginGlassPanel(5.0)
        self._glass_panels.append(sidebar)
        sidebar.setFixedWidth(265)
        sidebar.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 18, 0, 18)
        layout.setSpacing(10)

        menu_items = [
            ("dashboard", "Dashboard"),
            ("data_master", "Data Master"),
            ("data_karyawan", "HRIS & Manpower"),
            ("data_divisi", "Data Divisi"),
            ("data_blok", "Data Blok"),
            ("transaksi", "Transaksi"),
            ("input_kegiatan", "Input Kegiatan"),
            ("absensi", "Absensi"),
            ("panen", "Panen"),
            ("laporan", "Laporan"),
            ("inventaris", "Inventaris"),
            ("pengaturan", "Pengaturan"),
            ("manajemen_user", "User Management"),
        ]

        for key, item_text in menu_items:
            item = AnimatedNavItem(item_text, active=(key == "dashboard"), item_key=key)
            item.clicked.connect(self._on_nav_clicked)
            self._nav_items[key] = item
            layout.addWidget(item)

        layout.addStretch(1)
        return sidebar

    def _on_nav_clicked(self, item_key: str) -> None:
        for key, item in self._nav_items.items():
            item.set_active(key == item_key)

        if item_key == "manajemen_user":
            self._content_stack.setCurrentWidget(self._management_user_page)
            self._load_users_table()
            return
        if item_key == "data_karyawan":
            self._refresh_hris_manpower_page()
            return

        self._refresh_dashboard_overview_page()

    def _refresh_dashboard_overview_page(self) -> None:
        refreshed_page = self._build_content()
        self._replace_stack_page(self._dashboard_overview_page, refreshed_page, make_current=True)
        self._dashboard_overview_page = refreshed_page

        if self._charging is not None:
            self._apply_dashboard_theme(bool(self._charging))

    def _refresh_hris_manpower_page(self) -> None:
        refreshed_page = self._build_hris_manpower_page()
        self._replace_stack_page(self._hris_manpower_page, refreshed_page, make_current=True)
        self._hris_manpower_page = refreshed_page

        if self._charging is not None:
            self._apply_dashboard_theme(bool(self._charging))

    def _replace_stack_page(self, previous_page: QWidget, refreshed_page: QWidget, *, make_current: bool) -> None:
        previous_index = self._content_stack.indexOf(previous_page)
        if previous_index >= 0:
            self._content_stack.removeWidget(previous_page)
            self._content_stack.insertWidget(previous_index, refreshed_page)
            previous_page.deleteLater()
        else:
            self._content_stack.addWidget(refreshed_page)

        if make_current:
            self._content_stack.setCurrentWidget(refreshed_page)

    def _read_hris_summary(self) -> dict[str, str]:
        return read_hris_summary(Session, _table_exists, _table_columns)

    def _read_hris_quality_issues(self, limit: int = 80) -> list[HrisQualityIssueRow]:
        status_value = (
            self._hris_quality_status_filter.currentText().strip().upper()
            if self._hris_quality_status_filter is not None
            else "OPEN"
        )
        severity_value = (
            self._hris_quality_severity_filter.currentText().strip().upper()
            if self._hris_quality_severity_filter is not None
            else "ALL"
        )
        search_value = (
            self._hris_quality_search.text().strip().lower()
            if self._hris_quality_search is not None
            else ""
        )
        return read_hris_quality_issues(
            Session,
            _table_exists,
            status_value=status_value,
            severity_value=severity_value,
            search_value=search_value,
            limit=limit,
        )

    def _read_hris_group_breakdown(self) -> list[tuple[str, str, str, str]]:
        return read_hris_group_breakdown(Session, _table_exists)

    def _build_hris_manpower_page(self) -> QWidget:
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("HRIS & Manpower Control")
        self._page_title_labels.append(title)
        layout.addWidget(title)

        subtitle = QLabel(
            "Kontrol tenaga kerja kebun: master karyawan, assignment aktif, status efektif, kontrak, BPJS, payroll profile, dokumen, dan audit perubahan."
        )
        subtitle.setWordWrap(True)
        self._dashboard_muted_labels.append(subtitle)
        layout.addWidget(subtitle)

        summary = self._read_hris_summary()
        warning_label = self._make_hris_data_warning_label(summary)
        if warning_label is not None:
            layout.addWidget(warning_label)
        group_rows = self._read_hris_group_breakdown()
        metric_grid = QGridLayout()
        metric_grid.setHorizontalSpacing(16)
        metric_grid.setVerticalSpacing(16)
        cards = [
            AnimatedInfoCard("HC", "Karyawan Aktif", f"{summary['active_employees']} / {summary['employees']}", "#50B4FF"),
            AnimatedInfoCard("DATA", "Kelengkapan Data", summary["data_completeness"], "#5BAE44"),
            AnimatedInfoCard("QA", "Data Quality", summary["data_quality_score"], "#F0C84B"),
            AnimatedInfoCard("GAP", "Assignment Gap", summary["assignment_missing"], "#D94A38"),
        ]
        self._info_cards.extend(cards)
        for index, card in enumerate(cards):
            metric_grid.addWidget(card, 0, index)
        layout.addLayout(metric_grid)

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(16)
        main_grid.setVerticalSpacing(16)

        category_card = AnimatedSectionCard("Manpower Category Map")
        self._section_cards.append(category_card)
        for code, name, detail, value in group_rows[:6]:
            category_card.body_layout.addWidget(
                self._make_hris_row(code, name, detail, value)
            )
        category_card.body_layout.addStretch(1)

        coverage_card = AnimatedSectionCard("Operational Coverage")
        self._section_cards.append(coverage_card)
        for code, title_text, detail, value in [
            (
                "ID",
                "Identitas & Alamat",
                f"{summary['identity_missing']} aktif belum punya identitas; {summary['address_missing']} belum punya alamat.",
                summary["data_completeness"],
            ),
            (
                "ASG",
                "Assignment Aktif",
                "Estate, divisi, posisi, dan kategori current disimpan sebagai histori kerja.",
                summary["active_assignments"],
            ),
            (
                "PAY",
                "Payroll Readiness",
                f"{summary['payroll_missing']} karyawan aktif belum punya payroll profile.",
                summary["payroll_profiles"],
            ),
            (
                "BPJS",
                "BPJS Coverage",
                f"Health {summary['bpjs_health_active']}; TK {summary['bpjs_tk_active']}; missing {summary['bpjs_missing']}.",
                summary["bpjs_health_active"],
            ),
            (
                "DOC",
                "Dokumen Karyawan",
                f"{summary['document_count']} dokumen tersimpan; {summary['document_missing']} aktif belum punya dokumen.",
                summary["document_count"],
            ),
        ]:
            coverage_card.body_layout.addWidget(self._make_hris_row(code, title_text, detail, value))
        coverage_card.body_layout.addStretch(1)

        control_card = AnimatedSectionCard("Legal, Payroll & Output Control")
        self._section_cards.append(control_card)
        for code, title_text, detail, value in [
            ("GROUP", "Kategori Manpower", "STF, BLN, SKU/PHT, PHL/KHL, dan BRG dipisah dari status legal.", summary["groups"]),
            ("LEGAL", "Status Legal", "PKWTT, PKWT, probation, KHL, dan borongan disimpan historis.", summary["employment_types"]),
            ("PAY", "Skema Upah", "Bulanan, HK, kg panen, dan output tidak dicampur dengan kategori.", summary["pay_schemes"]),
            ("JOB", "Job Family", "Panen, rawat, traksi, kantor, gudang, dan bibitan menjadi dimensi kerja.", summary["job_families"]),
            ("MOVE", "Movement 30 Hari", "Mutasi, promosi, demosi, cuti, keluar, dan perubahan data tercatat.", summary["movements_30d"]),
        ]:
            control_card.body_layout.addWidget(self._make_hris_row(code, title_text, detail, value))
        control_card.body_layout.addStretch(1)

        access_card = AnimatedSectionCard("Governance & Data Readiness")
        self._section_cards.append(access_card)
        for code, title_text, detail, value in [
            ("ORG", "Struktur Organisasi", f"{summary['companies']} company; {summary['estates']} estate; {summary['divisions']} divisi.", summary["positions"]),
            ("ACL", "Employee Permission", "Hak akses employee:view, create, update, status, delete, export.", summary["permissions"]),
            ("ATT", "Kode Absensi", "Kode H, S, I, A, CT dan nilai HK menjadi referensi absensi.", summary["attendance_codes"]),
            ("SNAP", "Schema Status", summary["latest_snapshot"], "Ready"),
            ("QA", "Data Quality Watch", f"{summary['future_assignment_starts']} tanggal aktif masa depan; {summary['source_date_reviews']} tanggal sumber dinormalisasi; {summary['age_review']} usia perlu verifikasi.", summary["quality_watch"]),
            ("DUP", "Duplicate Control", f"Employee no {summary['duplicate_employee_no']}; identitas {summary['duplicate_identity']}; assignment {summary['duplicate_current_assignments']}.", summary["contract_conflicts"]),
            ("WARN", "Contract Watch", "Kontrak jatuh tempo 30 hari ke depan.", summary["contracts_expiring_30"]),
        ]:
            access_card.body_layout.addWidget(self._make_hris_row(code, title_text, detail, value))
        access_card.body_layout.addStretch(1)

        main_grid.addWidget(category_card, 0, 0)
        main_grid.addWidget(coverage_card, 0, 1)
        main_grid.addWidget(control_card, 1, 0)
        main_grid.addWidget(access_card, 1, 1)
        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 1)
        layout.addLayout(main_grid, 1)

        quality_card = AnimatedSectionCard("Data Quality Drill-down")
        self._section_cards.append(quality_card)
        quality_header = QHBoxLayout()
        quality_header.setContentsMargins(0, 0, 0, 0)
        quality_header.setSpacing(10)
        self._hris_quality_summary_label = QLabel(
            f"Open {summary['quality_open_total']} | Blocking {summary['quality_open_blocking']} | Review {summary['quality_open_review']} | Info {summary['quality_open_info']} | Overdue {summary['quality_overdue']} | Import {summary['latest_import_batch']}"
        )
        self._hris_quality_summary_label.setWordWrap(True)
        self._dashboard_muted_labels.append(self._hris_quality_summary_label)
        self._hris_quality_refresh_btn = QPushButton("Refresh")
        self._hris_quality_refresh_btn.setFixedSize(92, 32)
        self._hris_quality_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hris_quality_refresh_btn.clicked.connect(lambda _checked=False: self._refresh_hris_quality_table())
        quality_header.addWidget(self._hris_quality_summary_label, 1)
        quality_header.addWidget(self._hris_quality_refresh_btn)
        quality_card.body_layout.addLayout(quality_header)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(10)
        self._hris_quality_search = QLineEdit()
        self._hris_quality_search.setPlaceholderText("Search employee, issue, division")
        self._hris_quality_search.setFixedHeight(34)
        self._hris_quality_search.textChanged.connect(lambda _value: self._refresh_hris_quality_table())
        self._hris_quality_status_filter = QComboBox()
        self._hris_quality_status_filter.addItems(["OPEN", "VERIFIED", "IGNORED", "FIXED", "ALL"])
        self._hris_quality_status_filter.setFixedHeight(34)
        self._hris_quality_status_filter.currentTextChanged.connect(lambda _value: self._refresh_hris_quality_table())
        self._hris_quality_severity_filter = QComboBox()
        self._hris_quality_severity_filter.addItems(["ALL", "BLOCKING", "REVIEW", "INFO"])
        self._hris_quality_severity_filter.setFixedHeight(34)
        self._hris_quality_severity_filter.currentTextChanged.connect(lambda _value: self._refresh_hris_quality_table())
        filter_row.addWidget(self._hris_quality_search, 1)
        filter_row.addWidget(self._hris_quality_status_filter)
        filter_row.addWidget(self._hris_quality_severity_filter)
        quality_card.body_layout.addLayout(filter_row)

        workflow_row = QHBoxLayout()
        workflow_row.setContentsMargins(0, 0, 0, 0)
        workflow_row.setSpacing(10)
        self._hris_quality_verify_selected_btn = QPushButton("Verify Selected")
        self._hris_quality_ignore_selected_btn = QPushButton("Ignore Selected")
        self._hris_quality_fixed_selected_btn = QPushButton("Fixed Selected")
        self._hris_quality_export_btn = QPushButton("Export Filter")
        for button in (
            self._hris_quality_verify_selected_btn,
            self._hris_quality_ignore_selected_btn,
            self._hris_quality_fixed_selected_btn,
            self._hris_quality_export_btn,
        ):
            button.setFixedHeight(32)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._hris_quality_action_buttons.append(button)
            workflow_row.addWidget(button)
        self._hris_quality_verify_selected_btn.clicked.connect(
            lambda _checked=False: self._bulk_set_hris_quality_status("VERIFIED")
        )
        self._hris_quality_ignore_selected_btn.clicked.connect(
            lambda _checked=False: self._bulk_set_hris_quality_status("IGNORED")
        )
        self._hris_quality_fixed_selected_btn.clicked.connect(
            lambda _checked=False: self._bulk_set_hris_quality_status("FIXED")
        )
        self._hris_quality_export_btn.clicked.connect(lambda _checked=False: self._export_filtered_hris_quality_issues())
        can_manage_quality = self._can_current_user_manage_hris_quality()
        for button in (
            self._hris_quality_verify_selected_btn,
            self._hris_quality_ignore_selected_btn,
            self._hris_quality_fixed_selected_btn,
        ):
            button.setEnabled(can_manage_quality)
            if not can_manage_quality:
                button.setToolTip("Only Active Superior or Administrator users can update Data Quality workflow.")
        can_export_quality = self._can_current_user_export_hris_quality()
        self._hris_quality_export_btn.setEnabled(can_export_quality)
        if not can_export_quality:
            self._hris_quality_export_btn.setToolTip("Data Quality export permission is required.")
        workflow_row.addStretch(1)
        quality_card.body_layout.addLayout(workflow_row)

        self._hris_quality_table = self._build_hris_quality_table()
        quality_card.body_layout.addWidget(self._hris_quality_table)
        layout.addWidget(quality_card)

        page.setWidget(content)
        return page

    def _build_hris_quality_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels(
            [
                "Severity",
                "Status",
                "Issue",
                "Employee",
                "Division",
                "Age",
                "SLA",
                "Observed",
                "Recommendation",
                "Workflow",
            ]
        )
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setMinimumHeight(300)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        table.itemDoubleClicked.connect(self._open_hris_employee_detail_from_issue_item)
        self._refresh_hris_quality_table(table)
        return table

    def _refresh_hris_quality_table(self, table: Optional[QTableWidget] = None) -> None:
        target_table = table or self._hris_quality_table
        if target_table is None:
            return
        self._refresh_hris_quality_summary_label()
        rows = self._read_hris_quality_issues()
        target_table.clearSpans()
        target_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["severity"],
                row["status"],
                row["issue"],
                row["employee"],
                row["division"],
                row["age_days"],
                row["sla"],
                row["observed"],
                row["recommendation"],
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                item.setData(Qt.ItemDataRole.UserRole, row["issue_id"])
                item.setData(Qt.ItemDataRole.UserRole + 1, row["employee_id"])
                if column_index in {0, 1, 2, 4, 5, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                target_table.setItem(row_index, column_index, item)
            target_table.setCellWidget(
                row_index,
                9,
                self._build_hris_quality_action_widget(row["issue_id"], row["status"], row["employee_id"]),
            )
            target_table.setRowHeight(row_index, 46)
        if not rows:
            target_table.setRowCount(1)
            item = QTableWidgetItem("Tidak ada open issue.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            target_table.setSpan(0, 0, 1, 10)
            target_table.setItem(0, 0, item)

    def _refresh_hris_quality_summary_label(self) -> None:
        if self._hris_quality_summary_label is None:
            return
        summary = self._read_hris_summary()
        self._hris_quality_summary_label.setText(
            f"Open {summary['quality_open_total']} | Blocking {summary['quality_open_blocking']} | "
            f"Review {summary['quality_open_review']} | Info {summary['quality_open_info']} | "
            f"Overdue {summary['quality_overdue']} | Import {summary['latest_import_batch']}"
        )

    def _build_hris_quality_action_widget(self, issue_id: int, current_status: str, employee_id: int) -> QWidget:
        wrapper = QWidget()
        wrapper.setAutoFillBackground(False)
        wrapper.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        actions = [
            ("Detail", "DETAIL", "secondary"),
            ("Verify", "VERIFIED", "primary"),
            ("Ignore", "IGNORED", "secondary"),
            ("Fixed", "FIXED", "primary"),
        ]
        can_manage_quality = self._can_current_user_manage_hris_quality()
        for label, status, role in actions:
            button = QPushButton(label)
            button.setFixedSize(62, 26)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._apply_table_action_button_style(button, role)
            if status == "DETAIL":
                button.setEnabled(employee_id > 0)
                button.clicked.connect(
                    lambda _checked=False, target_issue_id=issue_id: self._open_hris_employee_detail_from_issue(
                        target_issue_id
                    )
                )
            else:
                button.setEnabled(can_manage_quality and current_status != status)
                if not can_manage_quality:
                    button.setToolTip("Only Active Superior or Administrator users can update Data Quality workflow.")
                button.clicked.connect(
                    lambda _checked=False, target_issue_id=issue_id, target_status=status: self._set_hris_quality_issue_status(
                        target_issue_id,
                        target_status,
                    )
                )
            layout.addWidget(button)
        return wrapper

    def _open_hris_employee_detail_from_issue_item(self, item: QTableWidgetItem) -> None:
        issue_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(issue_id, int):
            self._open_hris_employee_detail_from_issue(issue_id)

    def _open_hris_employee_detail_from_issue(self, issue_id: int) -> None:
        employee_id = read_hris_employee_id_for_issue(Session, issue_id=issue_id)
        if employee_id <= 0:
            QMessageBox.information(self, "Employee Detail", "Issue ini tidak terhubung ke karyawan tertentu.")
            return
        detail = self._read_hris_employee_detail(employee_id, issue_id)
        if detail is None:
            QMessageBox.information(self, "Employee Detail", "Detail karyawan tidak ditemukan.")
            return
        self._show_hris_employee_detail_dialog(detail)

    def _read_hris_employee_detail(self, employee_id: int, issue_id: int | None = None) -> dict[str, str] | None:
        return read_hris_employee_detail(
            Session,
            _table_exists,
            employee_id=employee_id,
            issue_id=issue_id,
        )

    def _show_hris_employee_detail_dialog(self, detail: dict[str, str]) -> None:
        dialog = DashboardGlassDialog(self, radius=18.0)
        dialog.set_charging(bool(self._charging))
        dialog.setWindowTitle("Employee Detail")
        dialog.setModal(True)
        dialog.resize(760, 620)
        dialog.setStyleSheet(_dashboard_dialog_stylesheet(bool(self._charging)))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel(f"{detail['employee_no']} - {detail['full_name']}")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 20px; font-weight: 900; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel(
            f"{detail['division_name']} | {detail['position_name']} | {detail['status_code']}"
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        for section_title, rows in [
            (
                "Profile",
                [
                    ("Gender", detail["gender"]),
                    ("Tempat/Tanggal Lahir", f"{detail['birth_place']} / {detail['birth_date']}"),
                    ("Agama", detail["religion"]),
                    ("Pendidikan", detail["education"]),
                    ("Status Keluarga", detail["marital_status"]),
                    ("Status Aktif", detail["active_flag"]),
                ],
            ),
            (
                "Assignment & Legal",
                [
                    ("Estate", detail["estate_name"]),
                    ("Divisi", detail["division_name"]),
                    ("Posisi", detail["position_name"]),
                    ("Kategori", detail["category_name"]),
                    ("Mulai Assignment", detail["assignment_start"]),
                    ("Status Efektif", f"{detail['status_name']} / {detail['status_effective']}"),
                    ("Tipe Kontrak", detail["employment_type"]),
                    ("Kontrak", f"{detail['contract_no']} / {detail['contract_start']} - {detail['contract_end']}"),
                ],
            ),
            (
                "Completeness",
                [
                    ("Identitas", detail["identity_count"]),
                    ("Alamat", detail["address_count"]),
                    ("BPJS Aktif", detail["bpjs_count"]),
                    ("Dokumen", detail["document_count"]),
                    ("Open Issues", detail["open_issues"]),
                    ("Blocking / Review / Info", f"{detail['blocking_issues']} / {detail['review_issues']} / {detail['info_issues']}"),
                ],
            ),
            (
                "Selected Issue",
                [
                    ("Issue", detail["issue_code"]),
                    ("Severity / Status", f"{detail['issue_severity']} / {detail['issue_status']}"),
                    ("Observed", detail["issue_observed"]),
                    ("Recommendation", detail["issue_recommendation"]),
                ],
            ),
        ]:
            section = AnimatedSectionCard(section_title)
            section.set_charging(bool(self._charging))
            for label_text, value_text in rows:
                section.body_layout.addWidget(self._make_hris_detail_row(label_text, value_text))
            body_layout.addWidget(section)

        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        close_button = QPushButton("Close")
        close_button.setFixedHeight(36)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _make_hris_detail_row(self, label_text: str, value_text: str) -> QWidget:
        palette = _charging_theme_palette(bool(self._charging))
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        label = QLabel(label_text)
        label.setFixedWidth(160)
        label.setWordWrap(True)
        label.setStyleSheet(
            f"color: {palette['panel_muted']}; font-size: 12px; font-weight: 800; background: transparent;"
        )
        value = QLabel(value_text)
        value.setWordWrap(True)
        value.setStyleSheet(
            f"color: {palette['panel_text']}; font-size: 13px; font-weight: 700; background: transparent;"
        )
        row_layout.addWidget(label)
        row_layout.addWidget(value, 1)
        return row

    def _make_hris_data_warning_label(self, summary: dict[str, str]) -> Optional[QLabel]:
        if summary.get("data_warning") != "1":
            return None
        warning = QLabel("Data sync warning: sebagian metrik memakai fallback karena query HRIS gagal.")
        warning.setWordWrap(True)
        warning.setProperty("badgeColor", "#F6EEBD")
        self._dashboard_badges.append(warning)
        return warning

    def _set_hris_quality_issue_status(self, issue_id: int, status: str) -> None:
        self._set_hris_quality_issue_statuses([issue_id], status)

    def _selected_hris_quality_issue_ids(self) -> list[int]:
        if self._hris_quality_table is None:
            return []
        issue_ids: set[int] = set()
        for item in self._hris_quality_table.selectedItems():
            value = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(value, int):
                issue_ids.add(value)
        return sorted(issue_ids)

    def _bulk_set_hris_quality_status(self, status: str) -> None:
        if not self._can_current_user_manage_hris_quality():
            self._show_hris_quality_access_denied_dialog()
            return
        issue_ids = self._selected_hris_quality_issue_ids()
        if not issue_ids:
            QMessageBox.information(self, "Data Quality", "Pilih satu atau beberapa issue terlebih dahulu.")
            return
        self._set_hris_quality_issue_statuses(issue_ids, status)

    def _set_hris_quality_issue_statuses(self, issue_ids: list[int], status: str) -> None:
        if not self._can_current_user_manage_hris_quality():
            self._show_hris_quality_access_denied_dialog()
            return
        if not issue_ids:
            return

        updated, error_message = update_hris_quality_issue_statuses(
            Session,
            _table_exists,
            _table_columns,
            user_id=self.current_user_id() or None,
            issue_ids=issue_ids,
            status=status,
        )
        if not updated:
            QMessageBox.warning(self, "Data Quality", f"Gagal update issue: {error_message}")
            return
        self._refresh_hris_quality_table()
        self._refresh_dashboard_overview_page_in_background()

    def _refresh_dashboard_overview_page_in_background(self) -> None:
        if self._content_stack.currentWidget() is self._dashboard_overview_page:
            self._refresh_dashboard_overview_page()
            return

        refreshed_page = self._build_content()
        self._replace_stack_page(self._dashboard_overview_page, refreshed_page, make_current=False)
        self._dashboard_overview_page = refreshed_page
        if self._charging is not None:
            self._apply_dashboard_theme(bool(self._charging))

    def _export_filtered_hris_quality_issues(self) -> None:
        if not self._can_current_user_export_hris_quality():
            self._show_hris_quality_export_access_denied_dialog()
            return

        rows = self._read_hris_quality_issues(limit=100_000)
        if not rows:
            QMessageBox.information(self, "Data Quality", "Tidak ada issue pada filter saat ini.")
            return

        output_path = export_hris_quality_issues(
            rows,
            reports_dir=DEFAULT_REPORTS_DIR,
            session_factory=Session,
            table_exists=_table_exists,
            table_columns=_table_columns,
            user_id=self.current_user_id() or None,
            status_filter=(
                self._hris_quality_status_filter.currentText().strip()
                if self._hris_quality_status_filter is not None
                else "OPEN"
            ),
            severity_filter=(
                self._hris_quality_severity_filter.currentText().strip()
                if self._hris_quality_severity_filter is not None
                else "ALL"
            ),
            search_text=(
                self._hris_quality_search.text().strip()
                if self._hris_quality_search is not None
                else ""
            ),
        )

        QMessageBox.information(
            self,
            "Data Quality",
            f"Export selesai: {output_path}",
        )

    def _make_hris_row(self, code: str, title_text: str, detail_text: str = "", value_text: str = "") -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        code_label = QLabel(code)
        code_label.setFixedWidth(88)
        code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_label.setProperty("badgeColor", "#D7E8F8")
        self._dashboard_badges.append(code_label)

        text_stack = QVBoxLayout()
        text_stack.setContentsMargins(0, 0, 0, 0)
        text_stack.setSpacing(2)

        title_label = QLabel(title_text)
        title_label.setWordWrap(True)
        self._dashboard_text_labels.append(title_label)
        text_stack.addWidget(title_label)

        if detail_text:
            detail_label = QLabel(detail_text)
            detail_label.setWordWrap(True)
            self._dashboard_muted_labels.append(detail_label)
            text_stack.addWidget(detail_label)

        row_layout.addWidget(code_label)
        row_layout.addLayout(text_stack, 1)
        if value_text:
            value_label = QLabel(value_text)
            value_label.setMinimumWidth(74)
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setProperty("badgeColor", "#D7E8F8")
            self._dashboard_badges.append(value_label)
            row_layout.addWidget(value_label)
        return row

    def _build_management_users_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self._page_title_label = QLabel("User Management")
        self._page_title_labels.append(self._page_title_label)
        layout.addWidget(self._page_title_label)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._search_username = QLineEdit()
        self._search_username.setPlaceholderText("Search username...")
        self._search_username.setFixedHeight(36)
        self._search_username.textChanged.connect(self._apply_user_filters)

        filter_label = QLabel("Role Filter")
        self._dashboard_text_labels.append(filter_label)

        self._role_filter = QComboBox()
        self._role_filter.addItem("All")
        self._role_filter.setFixedHeight(36)
        self._role_filter.setMinimumWidth(180)
        self._role_filter.currentTextChanged.connect(self._apply_user_filters)

        self._add_user_btn = QPushButton("+ Add User")
        self._add_user_btn.setFixedHeight(36)
        self._add_user_btn.setMinimumWidth(140)
        self._add_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_user_btn.clicked.connect(self._open_add_user_dialog)

        controls.addWidget(self._search_username, 2)
        controls.addStretch(1)
        controls.addWidget(filter_label)
        controls.addWidget(self._role_filter)
        controls.addWidget(self._add_user_btn)
        layout.addLayout(controls)

        self._users_table = QTableWidget()
        self._users_table.setColumnCount(9)
        self._users_table.setHorizontalHeaderLabels(
            [
                "FULL NAME",
                "USERNAME",
                "ROLE",
                "EMAIL",
                "PHONE",
                "UPDATED",
                "STATUS",
                "ID",
                "ACTIONS",
            ]
        )
        self._users_table.verticalHeader().setVisible(False)
        self._users_table.verticalHeader().setDefaultSectionSize(62)
        self._users_table.setAlternatingRowColors(True)
        self._users_table.setShowGrid(False)
        self._users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._users_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self._users_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self._users_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._users_table.setWordWrap(False)
        self._users_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._users_table.setStyleSheet(
            "QTableWidget { background: rgba(23, 31, 42, 0.78); alternate-background-color: rgba(38, 47, 59, 0.72); "
            "color: #F4F8FF; border: 1px solid rgba(255, 255, 255, 0.26); border-radius: 12px; font-size: 14px; outline: none; }"
            "QHeaderView::section { background: rgba(43, 52, 65, 0.86); color: rgba(230, 237, 246, 0.72); "
            "font-size: 11px; font-weight: 800; border: none; border-bottom: 1px solid rgba(255,255,255,0.18); padding: 10px 14px; }"
            "QTableWidget::item { padding: 10px 12px; border: none; }"
            "QTableWidget::item:hover { background: rgba(255, 255, 255, 0.09); }"
            "QTableWidget::item:selected { background: rgba(255, 255, 255, 0.16); color: #F4F8FF; }"
        )

        header = self._users_table.horizontalHeader()
        header.setMinimumSectionSize(72)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Widget-based columns should keep fixed width for consistent pixel alignment.
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        header.setSectionsClickable(True)
        header.setStretchLastSection(False)
        header.sectionDoubleClicked.connect(self._auto_size_user_table_column)
        section_handle_double_clicked = getattr(header, "sectionHandleDoubleClicked", None)
        if section_handle_double_clicked is not None:
            section_handle_double_clicked.connect(self._auto_size_user_table_column)

        # Default widths tuned for readability while keeping manual resize enabled.
        self._users_table.setColumnWidth(0, 210)
        self._users_table.setColumnWidth(1, 165)
        self._users_table.setColumnWidth(2, 108)
        self._users_table.setColumnWidth(3, 220)
        self._users_table.setColumnWidth(4, 140)
        self._users_table.setColumnWidth(5, 150)
        self._users_table.setColumnWidth(6, 176)
        self._users_table.setColumnWidth(7, 72)
        self._users_table.setColumnWidth(8, 210)
        self._users_table.setColumnHidden(7, True)

        # Double-click row → edit; right-click → context menu; keyboard Delete/Enter
        self._users_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._users_table.customContextMenuRequested.connect(self._show_user_context_menu)
        self._users_table.cellDoubleClicked.connect(self._on_user_table_double_click)
        self._users_table.itemSelectionChanged.connect(self._sync_user_table_widget_states)
        self._users_table.installEventFilter(self)

        layout.addWidget(self._users_table, 1)
        return page

    def _auto_size_user_table_column(self, logical_index: int) -> None:
        if self._users_table is None:
            return

        # Keep widget-based columns fixed to avoid visual drift.
        if logical_index in {6, 8}:
            return

        self._users_table.resizeColumnToContents(logical_index)
        fitted_width = self._users_table.columnWidth(logical_index)
        padded_width = fitted_width + 18
        self._users_table.setColumnWidth(logical_index, max(72, min(padded_width, 520)))

    def _auto_fit_all_user_columns(self) -> None:
        """Resize all columns to fit their content, with padding and a max cap."""
        if self._users_table is None:
            return
        self._users_table.resizeColumnsToContents()
        for col in range(self._users_table.columnCount() - 1):
            if self._users_table.isColumnHidden(col):
                continue
            w = self._users_table.columnWidth(col)
            self._users_table.setColumnWidth(col, max(72, min(w + 20, 320)))
        # Keep hidden ID internal-only and lock columns that use custom widgets.
        self._users_table.setColumnWidth(6, 176)
        self._users_table.setColumnWidth(8, 210)

    def _build_status_badge(self, status_value: str) -> QWidget:
        is_active = status_value.strip().lower() == "active"

        container = QWidget()
        container.setObjectName("statusBadgeContainer")
        container.setAutoFillBackground(False)
        container.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(container)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Pill widget — explicit QWidget so border-radius fills correctly
        pill = QWidget()
        pill.setObjectName("statusBadgePill")
        pill.setProperty("isActive", is_active)
        pill.setProperty("rowSelected", False)
        pill.setFixedSize(124, 32)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(10, 0, 12, 0)
        pill_layout.setSpacing(5)
        pill_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Colored dot indicator
        dot = QLabel()
        dot.setObjectName("statusBadgeDot")
        dot.setFixedSize(10, 10)

        # Text label
        lbl = QLabel(status_value)
        lbl.setObjectName("statusBadgeLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self._apply_status_badge_style(pill, dot, lbl, is_active, selected=False)

        pill_layout.addWidget(dot)
        pill_layout.addWidget(lbl)
        outer.addWidget(pill)
        return container

    def _apply_status_badge_style(
        self,
        pill: QWidget,
        dot: QLabel,
        lbl: QLabel,
        is_active: bool,
        selected: bool,
    ) -> None:
        charging = bool(self._charging)
        if is_active:
            if charging:
                pill_bg = "rgba(72, 187, 120, 0.20)" if not selected else "rgba(72, 187, 120, 0.28)"
                pill_border = "rgba(126, 232, 255, 0.28)" if not selected else "rgba(126, 232, 255, 0.42)"
                dot_color = "#48E08A"
                text_color = "#DFFFEA"
            elif selected:
                pill_bg = "rgba(72, 187, 120, 0.22)"
                pill_border = "rgba(255, 255, 255, 0.28)"
                dot_color = "#68D391"
                text_color = "#E9FDF0"
            else:
                pill_bg = "rgba(72, 187, 120, 0.16)"
                pill_border = "rgba(255, 255, 255, 0.20)"
                dot_color = "#68D391"
                text_color = "#E9FDF0"
        else:
            if charging:
                pill_bg = "rgba(255, 106, 106, 0.18)" if not selected else "rgba(255, 106, 106, 0.26)"
                pill_border = "rgba(126, 232, 255, 0.22)" if not selected else "rgba(126, 232, 255, 0.38)"
                dot_color = "#FF7B7B"
                text_color = "#FFE3E3"
            elif selected:
                pill_bg = "rgba(255, 106, 106, 0.22)"
                pill_border = "rgba(255, 255, 255, 0.26)"
                dot_color = "#FF8A8A"
                text_color = "#FFE3E3"
            else:
                pill_bg = "rgba(255, 106, 106, 0.15)"
                pill_border = "rgba(255, 255, 255, 0.18)"
                dot_color = "#FF8A8A"
                text_color = "#FFE3E3"

        pill.setStyleSheet(f"background: {pill_bg}; border: 1px solid {pill_border}; border-radius: 12px;")
        dot.setStyleSheet(f"QLabel {{ background: {dot_color}; border-radius: 4px; border: none; }}")
        lbl.setStyleSheet(
            f"QLabel {{ color: {text_color}; font-size: 12px; font-weight: 700; background: transparent; border: none; }}"
        )

    def _apply_table_action_button_style(self, button: QPushButton, role: str) -> None:
        charging = bool(self._charging)
        if role == "primary":
            if charging:
                button.setStyleSheet(
                    "QPushButton { background: rgba(80, 180, 255, 0.25); color: #ECFCFF; "
                    "border: 1px solid rgba(126, 232, 255, 0.45); border-radius: 6px; "
                    "font-size: 12px; font-weight: 700; }"
                    "QPushButton:hover { background: rgba(80, 180, 255, 0.34); }"
                    "QPushButton:pressed { background: rgba(80, 180, 255, 0.18); }"
                    "QPushButton:disabled { background: rgba(255, 255, 255, 0.09); color: rgba(236, 252, 255, 0.44); }"
                )
                return
            button.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.14); color: #F4F8FF; "
                "border: 1px solid rgba(255, 255, 255, 0.28); border-radius: 6px; "
                "font-size: 12px; font-weight: 700; }"
                "QPushButton:hover { background: rgba(255, 255, 255, 0.20); }"
                "QPushButton:pressed { background: rgba(255, 255, 255, 0.11); }"
                "QPushButton:disabled { background: rgba(255, 255, 255, 0.08); color: rgba(244, 248, 255, 0.44); }"
            )
            return

        if charging:
            button.setStyleSheet(
                "QPushButton { background: rgba(236, 252, 255, 0.08); color: #ECFCFF; "
                "border: 1px solid rgba(126, 232, 255, 0.32); border-radius: 6px; "
                "font-size: 13px; font-weight: 800; padding: 0; }"
                "QPushButton:hover { background: rgba(80, 180, 255, 0.18); border-color: rgba(126, 232, 255, 0.52); }"
                "QPushButton:pressed { background: rgba(80, 180, 255, 0.12); }"
            )
            return
        button.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.08); color: #F4F8FF; "
            "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 6px; "
            "font-size: 13px; font-weight: 800; padding: 0; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.14); border-color: rgba(255, 255, 255, 0.34); }"
            "QPushButton:pressed { background: rgba(255, 255, 255, 0.10); }"
        )

    def _sync_user_table_widget_states(self) -> None:
        if self._users_table is None:
            return

        for row_index in range(self._users_table.rowCount()):
            is_selected = self._users_table.selectionModel().isRowSelected(
                row_index,
                self._users_table.rootIndex(),
            )

            status_container = cast(Optional[QWidget], self._users_table.cellWidget(row_index, 6))
            if status_container is not None:
                pill = status_container.findChild(QWidget, "statusBadgePill")
                dot = status_container.findChild(QLabel, "statusBadgeDot")
                lbl = status_container.findChild(QLabel, "statusBadgeLabel")
                if pill is not None and dot is not None and lbl is not None:
                    is_active = bool(pill.property("isActive"))
                    self._apply_status_badge_style(pill, dot, lbl, is_active, is_selected)
                    pill.setProperty("rowSelected", is_selected)

            actions_container = cast(Optional[QWidget], self._users_table.cellWidget(row_index, 8))
            if actions_container is not None:
                edit_btn = actions_container.findChild(QPushButton, "userActionEditButton")
                more_btn = actions_container.findChild(QPushButton, "userActionMoreButton")
                if edit_btn is not None:
                    self._apply_table_action_button_style(edit_btn, "primary")
                if more_btn is not None:
                    self._apply_table_action_button_style(more_btn, "secondary")

    def _row_data_from_table(self, row: int) -> Optional[tuple[int, str, str, str, str, str]]:
        if self._users_table is None:
            return None
        item = self._users_table.item(row, 0)
        if item is None:
            return None
        raw = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(raw, tuple) or len(raw) != 6:  # type: ignore[arg-type]
            return None
        return cast(tuple[int, str, str, str, str, str], raw)

    def _on_user_table_double_click(self, row: int, _column: int) -> None:
        data = self._row_data_from_table(row)
        if not data:
            return
        user_id, role_value, status_value, password_value, pin_value, _username = data
        self._edit_user(int(user_id), str(role_value), str(status_value), str(password_value), str(pin_value))

    def _show_user_context_menu(self, pos: object) -> None:
        if self._users_table is None:
            return
        index = self._users_table.indexAt(pos)  # type: ignore[arg-type]
        if not index.isValid():
            return
        data = self._row_data_from_table(index.row())
        if not data:
            return
        user_id, role_value, status_value, password_value, pin_value, username = data
        self._show_user_actions_menu(
            self._users_table.viewport().mapToGlobal(pos),  # type: ignore[arg-type]
            int(user_id),
            str(role_value),
            str(status_value),
            str(password_value),
            str(pin_value),
            str(username),
        )

    def _show_user_actions_menu(
        self,
        global_pos: object,
        user_id: int,
        role_value: str,
        status_value: str,
        password_value: str,
        pin_value: str,
        username: str,
    ) -> None:
        menu = QMenu(self)
        if bool(self._charging):
            menu.setStyleSheet(
                "QMenu { background: #14283A; border: 1px solid rgba(126, 232, 255, 0.34); border-radius: 8px; padding: 4px; font-size: 13px; }"
                "QMenu::item { padding: 7px 20px; border-radius: 5px; color: #ECFCFF; }"
                "QMenu::item:selected { background: rgba(80, 180, 255, 0.20); color: #FFFFFF; }"
                "QMenu::separator { height: 1px; background: rgba(126, 232, 255, 0.18); margin: 3px 8px; }"
            )
        else:
            menu.setStyleSheet(
                "QMenu { background: #1F2732; border: 1px solid rgba(255, 255, 255, 0.24); border-radius: 8px; padding: 4px; font-size: 13px; }"
                "QMenu::item { padding: 7px 20px; border-radius: 5px; color: #F4F8FF; }"
                "QMenu::item:selected { background: rgba(255, 255, 255, 0.14); color: #FFFFFF; }"
                "QMenu::separator { height: 1px; background: rgba(255, 255, 255, 0.14); margin: 3px 8px; }"
            )
        edit_action = menu.addAction("Edit User")
        can_manage_actions = self._can_current_user_manage_user_actions()
        if not can_manage_actions:
            edit_action.setToolTip("Only Active Superior users can perform Edit/Delete actions.")
        menu.addSeparator()
        delete_action = menu.addAction("Delete User")
        if not can_manage_actions:
            delete_action.setToolTip("Only Active Superior users can perform Edit/Delete actions.")
        action = menu.exec(global_pos)  # type: ignore[arg-type]
        if action is edit_action:
            self._edit_user(user_id, role_value, status_value, password_value, pin_value)
        elif action is delete_action:
            self._delete_user(user_id, username)

    def _action_on_selected_user_row(self, action: str) -> None:
        if self._users_table is None:
            return
        selected = self._users_table.selectionModel().selectedRows()
        if not selected:
            return
        data = self._row_data_from_table(selected[0].row())
        if not data:
            return
        user_id, role_value, status_value, password_value, pin_value, username = data
        if action == "edit":
            self._edit_user(int(user_id), str(role_value), str(status_value), str(password_value), str(pin_value))
        elif action == "delete":
            self._delete_user(int(user_id), str(username))

    def eventFilter(self, source: object, event: object) -> bool:
        if source is self._users_table and isinstance(event, QKeyEvent):
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._action_on_selected_user_row("edit")
                return True
            if event.key() == Qt.Key.Key_Delete:
                self._action_on_selected_user_row("delete")
                return True
        return super().eventFilter(source, event)  # type: ignore[arg-type]

    def _load_users_table(self) -> None:
        if self._users_table is None or self._role_filter is None:
            return

        def _fmt_dt(value: object) -> str:
            if value is None:
                return "-"
            text = str(value).replace("T", " ")
            normalized = text.split("+", 1)[0].strip()
            if len(normalized) >= 16:
                normalized = normalized[:16]
            try:
                dt = datetime.strptime(normalized, "%Y-%m-%d %H:%M")
                today = datetime.now().date()
                delta = (today - dt.date()).days
                time_str = dt.strftime("%H:%M")
                if delta == 0:
                    return f"Today {time_str}"
                elif delta == 1:
                    return f"Yesterday {time_str}"
                elif 2 <= delta <= 6:
                    return dt.strftime("%a") + f" {time_str}"
                else:
                    return f"{dt.strftime('%b')} {dt.day}, {time_str}"
            except ValueError:
                return normalized

        session = Session()
        try:
            if _is_hris_auth_schema(session):
                rows = session.execute(
                    text(
                        """
                        SELECT
                            u.user_id,
                            u.username,
                            COALESCE(NULLIF(u.full_name, ''), u.username) AS full_name,
                            COALESCE(NULLIF(u.email, ''), '-') AS email,
                            COALESCE(NULLIF(u.phone, ''), '-') AS phone,
                            COALESCE(NULLIF(u.status, ''), CASE WHEN u.is_active THEN 'active' ELSE 'inactive' END) AS status,
                            u.password_hash IS NOT NULL AS has_password,
                            u.pin_hash IS NOT NULL AS has_pin,
                            u.created_at,
                            u.updated_at,
                            u.is_active,
                            u.is_locked,
                            array_agg(r.role_name ORDER BY r.role_name)
                                FILTER (WHERE r.role_name IS NOT NULL) AS role_names
                        FROM users u
                        LEFT JOIN user_roles ur ON ur.user_id = u.user_id
                        LEFT JOIN roles r ON r.role_id = ur.role_id
                        GROUP BY
                            u.user_id, u.username, u.full_name, u.email, u.phone, u.status,
                            u.password_hash, u.pin_hash,
                            u.created_at, u.updated_at, u.is_active, u.is_locked
                        ORDER BY u.user_id ASC
                        """
                    )
                ).mappings().all()

                self._all_users_rows = []
                role_values: set[str] = set()
                for row in rows:
                    role_names = _role_names_from_value(row.get("role_names"))
                    normalized_role = _map_hris_role_to_dashboard_role(role_names)
                    is_active = bool(row.get("is_active")) and not bool(row.get("is_locked"))
                    status = str(row.get("status") or "").strip().lower()
                    row_status = "Active" if is_active and status in {"aktif", "active"} else "Inactive"
                    row_data: UserRow = {
                        "id": int(row.get("user_id") or 0),
                        "username": str(row.get("username") or ""),
                        "full_name": str(row.get("full_name") or row.get("username") or ""),
                        "email": str(row.get("email") or "-"),
                        "phone": str(row.get("phone") or "-"),
                        "role": normalized_role,
                        "status": row_status,
                        "password_value": _credential_status_label(row.get("has_password")),
                        "pin_value": _credential_status_label(row.get("has_pin")),
                        "created_at": _fmt_dt(row.get("created_at")),
                        "updated_at": _fmt_dt(row.get("updated_at")),
                    }
                    self._all_users_rows.append(row_data)
                    role_values.add(normalized_role)

                self._role_filter.blockSignals(True)
                self._role_filter.clear()
                self._role_filter.addItem("All")
                for value in sorted(role_values):
                    self._role_filter.addItem(value)
                self._role_filter.setCurrentText("All")
                self._role_filter.blockSignals(False)

                if self._search_username is not None:
                    self._search_username.blockSignals(True)
                    self._search_username.clear()
                    self._search_username.blockSignals(False)

                self._apply_user_filters()
                self._auto_fit_all_user_columns()
                return

            # CRITICAL: Pre-load role_links before closing session to prevent DetachedInstanceError
            # when accessing user.role property later
            from sqlalchemy.orm import selectinload
            users = (
                session.query(User)
                .options(
                    selectinload(User.role_links).selectinload(UserRole.role),
                    selectinload(User.password_record),
                    selectinload(User.pin_record),
                )
                .order_by(User.id.asc())
                .all()
            )
            # Prime all role values while session is still open
            for user in users:
                getattr(user, "role", None)  # Force evaluation of role property before detach
        finally:
            session.close()

        self._all_users_rows = []
        role_values: set[str] = set()

        for user in users:
            user_id = int(getattr(user, "id", 0) or 0)
            username = str(getattr(user, "username", "") or "")
            full_name = str(getattr(user, "full_name", "") or "").strip()
            email = str(getattr(user, "email", "") or "").strip()
            phone = str(getattr(user, "phone", "") or "").strip()
            raw_role = str(getattr(user, "role", "Operator") or "Operator").strip()
            try:
                normalized_role = normalize_role_name(raw_role)
            except ValueError:
                normalized_role = raw_role
            status = str(getattr(user, "status", "aktif") or "aktif").strip().lower()
            created_at = _fmt_dt(getattr(user, "created_at", None))
            updated_at = _fmt_dt(getattr(user, "updated_at", None))
            password_record = getattr(user, "password_record", None)
            pin_record = getattr(user, "pin_record", None)
            row: UserRow = {
                "id": user_id,
                "username": username,
                "full_name": full_name or username.replace("_", " ").title(),
                "email": email or "-",
                "phone": phone or "-",
                "role": normalized_role,
                "status": "Active" if status in {"aktif", "active"} else "Inactive",
                "password_value": _credential_status_label(
                    getattr(password_record, "password_hash", None)
                ),
                "pin_value": _credential_status_label(getattr(pin_record, "pin_hash", None)),
                "created_at": created_at,
                "updated_at": updated_at,
            }
            self._all_users_rows.append(row)
            role_values.add(normalized_role)

        self._role_filter.blockSignals(True)
        self._role_filter.clear()
        self._role_filter.addItem("All")
        for value in sorted(role_values):
            self._role_filter.addItem(value)
        self._role_filter.setCurrentText("All")
        self._role_filter.blockSignals(False)

        # Always show full table content when this page is opened/reloaded.
        if self._search_username is not None:
            self._search_username.blockSignals(True)
            self._search_username.clear()
            self._search_username.blockSignals(False)

        self._apply_user_filters()
        self._auto_fit_all_user_columns()

    def _apply_user_filters(self) -> None:
        if self._users_table is None or self._search_username is None or self._role_filter is None:
            return

        search_value = self._search_username.text().strip().lower()
        selected_role = self._role_filter.currentText().strip()

        filtered_rows = [
            row
            for row in self._all_users_rows
            if (not search_value or search_value in row["username"].lower())
            and (selected_role == "All" or row["role"] == selected_role)
        ]

        can_manage_actions = self._can_current_user_manage_user_actions()

        self._users_table.setRowCount(len(filtered_rows))
        for row_index, row in enumerate(filtered_rows):
            # Hoist row scalars so lambdas and UserRole data share the same refs
            row_id = row["id"]
            row_role = str(row["role"])
            row_status = str(row["status"])
            row_password = str(row["password_value"])
            row_pin = str(row["pin_value"])
            row_username = str(row["username"])

            # Col 0 — Full Name (also carries full row data for row actions)
            full_name_item = QTableWidgetItem(str(row["full_name"]))
            full_name_item.setToolTip(str(row["full_name"]))
            full_name_item.setData(
                Qt.ItemDataRole.UserRole,
                (row_id, row_role, row_status, row_password, row_pin, row_username),
            )
            self._users_table.setItem(row_index, 0, full_name_item)

            username_item = QTableWidgetItem(row_username)
            username_item.setToolTip(row_username)
            self._users_table.setItem(row_index, 1, username_item)

            self._users_table.setItem(row_index, 2, QTableWidgetItem(row_role))

            email_item = QTableWidgetItem(str(row["email"]))
            email_item.setToolTip(str(row["email"]))
            self._users_table.setItem(row_index, 3, email_item)

            self._users_table.setItem(row_index, 4, QTableWidgetItem(str(row["phone"])))

            updated_item = QTableWidgetItem(str(row["updated_at"]))
            updated_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._users_table.setItem(row_index, 5, updated_item)

            status_value = row_status
            self._users_table.setCellWidget(row_index, 6, self._build_status_badge(status_value))

            self._users_table.setItem(row_index, 7, QTableWidgetItem(str(row_id)))

            actions = QWidget()
            actions.setAutoFillBackground(False)
            actions.setStyleSheet("background: transparent;")
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(10, 8, 10, 8)
            actions_layout.setSpacing(8)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("userActionEditButton")
            edit_btn.setFixedSize(102, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._apply_table_action_button_style(edit_btn, "primary")
            edit_btn.clicked.connect(
                lambda _checked=False, user_id=row_id, role_value=row_role, status_value=row_status, password_value=row_password, pin_value=row_pin: self._edit_user(
                    user_id,
                    role_value,
                    status_value,
                    password_value,
                    pin_value,
                )
            )
            if not can_manage_actions:
                edit_btn.setToolTip("Only Active Superior users can perform Edit/Delete actions.")

            more_btn = QPushButton("...")
            more_btn.setObjectName("userActionMoreButton")
            more_btn.setFixedSize(38, 28)
            more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._apply_table_action_button_style(more_btn, "secondary")
            more_btn.clicked.connect(
                lambda _checked=False, button=more_btn, user_id=row_id, role_value=row_role, status_value=row_status, password_value=row_password, pin_value=row_pin, username=row_username: self._show_user_actions_menu(
                    button.mapToGlobal(button.rect().bottomLeft()),
                    user_id,
                    role_value,
                    status_value,
                    password_value,
                    pin_value,
                    username,
                )
            )

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(more_btn)
            self._users_table.setCellWidget(row_index, 8, actions)
            self._users_table.setRowHeight(row_index, 62)

        self._sync_user_table_widget_states()

    def _show_user_management_notice(
        self,
        title: str,
        message: str,
        *,
        window_title: str = "User Management",
    ) -> None:
        _show_credentials_warning(
            self,
            title,
            message,
            bool(self._charging),
            333,
            window_title,
            "pin",
        )

    def _confirm_user_management_action(
        self,
        title: str,
        message: str,
        *,
        confirm_text: str,
        window_title: str = "User Management",
    ) -> bool:
        charging = bool(self._charging)
        palette = _charging_theme_palette(charging)
        dialog = DashboardGlassDialog(self, radius=18.0)
        dialog.set_charging(charging)
        dialog.setModal(True)
        dialog.setWindowTitle(window_title)
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            | Qt.WindowType.FramelessWindowHint
        )
        dialog.setFixedSize(386, 214)
        dialog.setStyleSheet(
            _dashboard_dialog_stylesheet(charging)
            + f"""
            QLabel#confirmWindowTitle {{
                color: {palette['panel_muted']};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.2px;
                background: transparent;
            }}
            QLabel#confirmTitle {{
                color: {palette['panel_text']};
                font-size: 15px;
                font-weight: 850;
                background: transparent;
            }}
            QLabel#confirmMessage {{
                color: {palette['panel_muted']};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }}
            QFrame#confirmSeparator {{
                background: {palette['panel_border']};
                border: none;
            }}
            """
        )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 12, 18, 16)
        layout.setSpacing(12)

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(window_title)
        title_label.setObjectName("confirmWindowTitle")
        title_bar.addWidget(title_label)
        title_bar.addStretch(1)
        layout.addLayout(title_bar)

        separator = QFrame()
        separator.setObjectName("confirmSeparator")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        headline = QLabel(title)
        headline.setObjectName("confirmTitle")
        headline.setWordWrap(True)
        layout.addWidget(headline)

        body = QLabel(message)
        body.setObjectName("confirmMessage")
        body.setWordWrap(True)
        layout.addWidget(body, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        confirm_btn = QPushButton(confirm_text)
        for button, role in ((cancel_btn, "secondary"), (confirm_btn, "primary")):
            button.setFixedSize(104, 34)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._apply_table_action_button_style(button, role)
            button_row.addWidget(button)
        layout.addLayout(button_row)

        cancel_btn.clicked.connect(dialog.reject)
        confirm_btn.clicked.connect(dialog.accept)

        if self.isVisible():
            center = self.frameGeometry().center()
            dialog_rect = dialog.frameGeometry()
            dialog_rect.moveCenter(center)
            dialog.move(dialog_rect.topLeft())

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _edit_user(
        self,
        user_id: int,
        fallback_role: str = "Operator",
        fallback_status: str = "Active",
        fallback_password: str = "",
        fallback_pin: str = "",
    ) -> None:
        if not self._can_current_user_manage_user_actions():
            self._show_user_action_access_denied_dialog("Edit")
            return

        session = Session()
        try:
            hris_auth_schema = _is_hris_auth_schema(session)
            if hris_auth_schema:
                user_row = session.execute(
                    text(
                        """
                        SELECT user_id, username, full_name, status, is_active, password_hash, pin_hash
                        FROM users
                        WHERE user_id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                ).mappings().first()
                if user_row is None:
                    self._show_user_management_notice("Data Not Found", "User not found.")
                    return
                user = None
                username_value = str(user_row.get("username") or "")
                full_name_value = str(user_row.get("full_name") or "")
                raw_role = fallback_role
                raw_status = "aktif" if bool(user_row.get("is_active")) else "nonaktif"
            else:
                user = session.get(User, user_id)
                if user is None:
                    self._show_user_management_notice("Data Not Found", "User not found.")
                    return
                username_value = str(getattr(user, "username", "") or "")
                full_name_value = str(getattr(user, "nama", "") or "")
                raw_role = str(getattr(user, "role", "") or "").strip()
                raw_status = str(getattr(user, "status", "") or "").strip()

            role_value = raw_role if raw_role else fallback_role

            status_value = raw_status if raw_status else fallback_status

            dialog = UserEditDialog(
                username=username_value,
                nama=full_name_value,
                role=role_value,
                status=status_value,
                current_password="",
                current_pin="",
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            payload = dialog.data()
            if not payload["username"]:
                self._show_user_management_notice("Validation", "Username cannot be empty.")
                return

            old_password = str(payload.get("old_password", "") or "")
            new_password = str(payload.get("new_password", "") or "")
            old_pin = str(payload.get("old_pin", "") or "")
            new_pin = str(payload.get("new_pin", "") or "")

            if old_password:
                if hris_auth_schema:
                    stored_hash = str(user_row.get("password_hash") or "")
                    password_valid = bool(
                        stored_hash
                        and verify_bcrypt_password is not None
                        and verify_bcrypt_password(old_password, stored_hash)
                    )
                else:
                    password_record = getattr(user, "password_record", None)
                    stored_salt = str(getattr(password_record, "password_salt", "") or "")
                    stored_hash = str(getattr(password_record, "password_hash", "") or "")
                    password_valid = bool(stored_salt and stored_hash and verify_password(old_password, stored_salt, stored_hash))
                if not stored_hash:
                    self._show_user_management_notice(
                        "Credential Unavailable",
                        "Current password is not available for this user.",
                    )
                    return
                if not password_valid:
                    self._show_user_management_notice(
                        "Incorrect Password",
                        "Current password is incorrect.",
                    )
                    return

            if old_pin:
                if hris_auth_schema:
                    stored_pin_hash = str(user_row.get("pin_hash") or "")
                    pin_valid = bool(
                        stored_pin_hash
                        and verify_bcrypt_password is not None
                        and verify_bcrypt_password(old_pin, stored_pin_hash)
                    )
                else:
                    pin_record = getattr(user, "pin_record", None)
                    stored_pin_salt = str(getattr(pin_record, "pin_salt", "") or "")
                    stored_pin_hash = str(getattr(pin_record, "pin_hash", "") or "")
                    pin_valid = bool(stored_pin_salt and stored_pin_hash and verify_pin_code(old_pin, stored_pin_salt, stored_pin_hash))
                if not stored_pin_hash:
                    self._show_user_management_notice(
                        "Credential Unavailable",
                        "Current PIN is not available for this user.",
                    )
                    return
                if not pin_valid:
                    self._show_user_management_notice("Incorrect PIN", "Current PIN is incorrect.")
                    return

            update_user(
                session,
                user_id,
                username=payload["username"],
                nama=payload["nama"],
                role=payload["role"],
                status=payload["status"],
                password=new_password,
            )

            if new_pin:
                set_user_pin(session, user_id, new_pin)
        except ValueError as error:
            self._show_user_management_notice("Validation", str(error))
            return
        finally:
            session.close()

        self._load_users_table()
        self._show_user_management_notice(
            "User Updated",
            "User profile and credentials were updated successfully.",
        )

    def _get_current_user_access_profile(self) -> tuple[str, str]:
        if self._user is None:
            return ("Unknown", "Inactive")

        # Always read latest role/status from DB to avoid stale in-memory user state.
        user_id = int(getattr(self._user, "id", 0) or 0)
        if user_id > 0:
            session = Session()
            try:
                if _is_hris_auth_schema(session):
                    row = session.execute(
                        text(
                            """
                            SELECT u.user_id, u.is_active, u.is_locked, u.status,
                                   array_agg(r.role_name ORDER BY r.role_name)
                                       FILTER (WHERE r.role_name IS NOT NULL) AS role_names
                            FROM users u
                            LEFT JOIN user_roles ur ON ur.user_id = u.user_id
                            LEFT JOIN roles r ON r.role_id = ur.role_id
                            WHERE u.user_id = :user_id
                            GROUP BY u.user_id, u.is_active, u.is_locked, u.status
                            """
                        ),
                        {"user_id": user_id},
                    ).mappings().first()
                    if row is not None:
                        role_value = _map_hris_role_to_dashboard_role(
                            _role_names_from_value(row.get("role_names"))
                        )
                        raw_status = str(row.get("status") or "").strip().lower()
                        is_active = bool(row.get("is_active")) and not bool(row.get("is_locked"))
                        status_value = "Active" if is_active and raw_status in {"aktif", "active"} else "Inactive"
                        return (role_value, status_value)

                user = session.get(User, user_id)
                if user is not None:
                    raw_role = str(getattr(user, "role", "Operator") or "Operator").strip()
                    try:
                        role_value = normalize_role_name(raw_role)
                    except ValueError:
                        role_value = raw_role if raw_role else "Unknown"

                    raw_status = str(getattr(user, "status", "nonaktif") or "nonaktif").strip().lower()
                    status_value = "Active" if raw_status in {"aktif", "active"} else "Inactive"
                    return (role_value, status_value)
            finally:
                session.close()

        raw_role = str(getattr(self._user, "role", "Operator") or "Operator").strip()
        try:
            role_value = normalize_role_name(raw_role)
        except ValueError:
            role_value = raw_role if raw_role else "Unknown"
        raw_status = str(getattr(self._user, "status", "nonaktif") or "nonaktif").strip().lower()
        status_value = "Active" if raw_status in {"aktif", "active"} else "Inactive"
        return (role_value, status_value)

    def _can_current_user_manage_user_actions(self) -> bool:
        role_value, status_value = self._get_current_user_access_profile()
        return role_value.strip().lower() == "superior" and status_value.strip().lower() == "active"

    def _current_user_has_permission(self, module_name: str, action_name: str) -> Optional[bool]:
        return current_user_has_permission(
            Session,
            _table_exists,
            _table_columns,
            user_id=self.current_user_id(),
            module_name=module_name,
            action_name=action_name,
        )

    def _can_current_user_manage_hris_quality(self) -> bool:
        permission_result = self._current_user_has_permission("data_quality", "update")
        if permission_result is not None:
            return permission_result
        permission_result = self._current_user_has_permission("employee", "update")
        if permission_result is not None:
            return permission_result

        role_value, status_value = self._get_current_user_access_profile()
        if status_value.strip().lower() != "active":
            return False
        return role_value.strip().lower() in {"superior", "administrator"}

    def _can_current_user_export_hris_quality(self) -> bool:
        permission_result = self._current_user_has_permission("data_quality", "export")
        if permission_result is not None:
            return permission_result
        permission_result = self._current_user_has_permission("employee", "export")
        if permission_result is not None:
            return permission_result

        role_value, status_value = self._get_current_user_access_profile()
        if status_value.strip().lower() != "active":
            return False
        return role_value.strip().lower() in {"superior", "administrator", "auditor"}

    def _can_current_user_edit_users(self) -> bool:
        # Backward-compatible alias for existing call sites.
        return self._can_current_user_manage_user_actions()

    def _show_hris_quality_access_denied_dialog(self) -> None:
        role_value, status_value = self._get_current_user_access_profile()
        QMessageBox.warning(
            self,
            "Data Quality Restricted",
            "Only Active Superior or Administrator users can update Data Quality workflow.\n\n"
            f"Current access: {role_value} / {status_value}",
        )

    def _show_hris_quality_export_access_denied_dialog(self) -> None:
        role_value, status_value = self._get_current_user_access_profile()
        QMessageBox.warning(
            self,
            "Data Quality Export Restricted",
            "Data Quality export permission is required.\n\n"
            f"Current access: {role_value} / {status_value}",
        )

    def _show_user_action_access_denied_dialog(self, action_name: str) -> None:
        role_value, status_value = self._get_current_user_access_profile()
        self._show_user_management_notice(
            "User Action Restricted",
            "Only Active Superior users can perform this action.\n\n"
            f"Action: {action_name}\nCurrent access: {role_value} / {status_value}",
        )

    def _delete_user(self, user_id: int, username: str) -> None:
        if not self._can_current_user_manage_user_actions():
            self._show_user_action_access_denied_dialog("Delete")
            return

        current_user_id = self.current_user_id()
        if current_user_id == user_id:
            self._show_user_management_notice(
                "Delete Blocked",
                "You cannot delete the currently signed-in user.",
            )
            return

        if not self._confirm_user_management_action(
            "Delete User",
            f"Delete user '{username}'? This action cannot be undone.",
            confirm_text="Delete",
        ):
            return

        session = Session()
        try:
            delete_user(session, user_id)
        except ValueError as error:
            self._show_user_management_notice("Delete Failed", str(error))
            return
        finally:
            session.close()

        self._load_users_table()
        self._show_user_management_notice(
            "User Deleted",
            f"User '{username}' was deleted successfully.",
        )

    def _open_change_password_dialog(self) -> None:
        """Buka dialog untuk user mengganti password dan PIN mereka sendiri"""
        if self._user is None:
            QMessageBox.warning(self, "Error", "User tidak ditemukan.")
            return

        dialog = ChangePasswordDialog(
            username=str(getattr(self._user, "username", "") or "User"),
            parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.data()
        old_password = str(payload.get("old_password", "") or "")
        new_password = str(payload.get("new_password", "") or "")
        old_pin = str(payload.get("old_pin", "") or "")
        new_pin = str(payload.get("new_pin", "") or "")

        # Validasi: both old dan new harus diisi jika ingin mengganti
        if new_password and not old_password:
            QMessageBox.warning(self, "Validasi", "Isi Password Lama untuk mengganti password.")
            return

        if new_pin and not old_pin:
            QMessageBox.warning(self, "Validasi", "Isi PIN Lama untuk mengganti PIN.")
            return

        if old_password and not new_password:
            QMessageBox.warning(self, "Validasi", "Isi Password Baru jika mengisi Password Lama.")
            return

        if old_pin and not new_pin:
            QMessageBox.warning(self, "Validasi", "Isi PIN Baru jika mengisi PIN Lama.")
            return

        # Validasi: minimal ada satu yang akan diubah
        if not (old_password or old_pin):
            QMessageBox.warning(self, "Validasi", "Minimal ganti password atau PIN.")
            return

        user_id = int(getattr(self._user, "id", 0) or 0)
        session = Session()
        try:
            # Reload user untuk pastikan data fresh
            user = session.get(User, user_id)
            if user is None:
                QMessageBox.warning(self, "Error", "User tidak ditemukan di database.")
                return

            # Verifikasi password lama
            if old_password:
                password_record = getattr(user, "password_record", None)
                stored_salt = str(getattr(password_record, "password_salt", "") or "")
                stored_hash = str(getattr(password_record, "password_hash", "") or "")
                if not stored_salt or not stored_hash:
                    QMessageBox.warning(self, "Validasi", "Password lama belum tersedia.")
                    return
                if not verify_password(old_password, stored_salt, stored_hash):
                    QMessageBox.warning(self, "Validasi", "Password lama tidak sesuai.")
                    return

            # Verifikasi PIN lama
            if old_pin:
                pin_record = getattr(user, "pin_record", None)
                stored_pin_salt = str(getattr(pin_record, "pin_salt", "") or "")
                stored_pin_hash = str(getattr(pin_record, "pin_hash", "") or "")
                if not stored_pin_salt or not stored_pin_hash:
                    QMessageBox.warning(self, "Validasi", "PIN lama belum tersedia.")
                    return
                if not verify_pin_code(old_pin, stored_pin_salt, stored_pin_hash):
                    QMessageBox.warning(self, "Validasi", "PIN lama tidak sesuai.")
                    return

            # Update password
            if new_password:
                update_user(session, user_id, password=new_password)

            # Update PIN
            if new_pin:
                set_user_pin(session, user_id, new_pin)

            # Audit log
            session.add(
                AuditLog(
                    user_id=user_id,
                    action="self_change_password",
                    action_type="security",
                    description="mengubah password dan/atau PIN sendiri",
                    ip_address=None,
                )
            )
            session.commit()
            
            QMessageBox.information(
                self,
                "Berhasil",
                "Password dan/atau PIN berhasil diubah.\nAnda akan logout, silakan login kembali.",
            )
            # Logout setelah password berubah untuk keamanan
            self.close()
        except ValueError as error:
            QMessageBox.warning(self, "Validasi", str(error))
            session.rollback()
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Gagal mengubah password/PIN: {error}")
            session.rollback()
        finally:
            session.close()

    def _open_add_user_dialog(self) -> None:
        """Open dialog to add a new user."""
        if not self._can_current_user_manage_user_actions():
            self._show_user_action_access_denied_dialog("Add")
            return

        dialog = UserAddDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        data = dialog.data()
        
        # Validasi
        if not data["username"]:
            self._show_user_management_notice("Validation", "Username cannot be empty.")
            return
        
        if not data["nama"]:
            self._show_user_management_notice("Validation", "Full name cannot be empty.")
            return
        
        self._add_user(data)

    def _add_user(self, data: dict[str, str]) -> None:
        """Add a new user to the database with generated password and PIN."""
        # Generate password dan PIN
        generated_password = self._build_temp_password()
        generated_pin = "".join(secrets.choice(string.digits) for _ in range(6))
        
        session = Session()
        try:
            try:
                from database.crud import create_user
            except ImportError:
                from src.database.crud import create_user  # type: ignore
            
            create_user(
                session,
                username=data["username"],
                nama=data["nama"],
                password=generated_password,
                role=data["role"],
                status=data["status"],
                pin=generated_pin,
            )
            
            self._load_users_table()
            self._show_user_management_notice(
                "Temporary Credentials",
                f"{data['username']} created.\nPassword: {generated_password}\nPIN: {generated_pin}\nShown only once.",
            )
        except ValueError as error:
            self._show_user_management_notice("Validation", str(error))
            session.rollback()
            return
        except Exception as error:
            self._show_user_management_notice("User Create Failed", f"Error: {error}")
            session.rollback()
            return
        finally:
            session.close()

    def _build_content(self) -> QWidget:
        summary = self._read_hris_summary()
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        top_cards = QGridLayout()
        top_cards.setHorizontalSpacing(16)
        top_cards.setVerticalSpacing(16)
        overview_cards = [
            AnimatedInfoCard("HC", "Karyawan Aktif", f"{summary['active_employees']} / {summary['employees']}", "#50B4FF"),
            AnimatedInfoCard("QA", "Data Quality", summary["data_quality_score"], "#5BAE44"),
            AnimatedInfoCard("ATT", "Absensi Hari Ini", f"{summary['attendance_present_today']} hadir", "#F0C84B"),
            AnimatedInfoCard("GAP", "Assignment Gap", summary["assignment_missing"], "#D94A38"),
        ]
        self._info_cards.extend(overview_cards)
        for index, card in enumerate(overview_cards):
            top_cards.addWidget(card, 0, index)
        layout.addLayout(top_cards)
        warning_label = self._make_hris_data_warning_label(summary)
        if warning_label is not None:
            layout.addWidget(warning_label)

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(16)
        main_grid.setVerticalSpacing(16)

        production = AnimatedSectionCard("Manpower Snapshot")
        self._section_cards.append(production)
        production.body_layout.addWidget(self._make_chart_placeholder(summary))
        production.body_layout.addStretch(1)

        attendance = AnimatedSectionCard("Absensi Karyawan")
        self._section_cards.append(attendance)
        attendance.body_layout.addWidget(self._make_attendance_placeholder(summary))

        tasks = AnimatedSectionCard("Control Watch")
        self._section_cards.append(tasks)
        for task_text, badge_text, badge_color in [
            ("Payroll profile belum lengkap", summary["payroll_missing"], "#D7E8F8"),
            ("Kontrak jatuh tempo 30 hari", summary["contracts_expiring_30"], "#F7D7D6"),
            ("Data quality overdue", summary["quality_overdue"], "#F6EEBD"),
        ]:
            tasks.body_layout.addWidget(self._make_task_row(task_text, badge_text, badge_color))

        notifications = AnimatedSectionCard("Notifikasi")
        self._section_cards.append(notifications)
        for line in [
            f"Import terakhir: {summary['latest_import_batch']} ({summary['latest_import_rows']} baris).",
            f"BPJS missing: {summary['bpjs_missing']} | Dokumen missing: {summary['document_missing']}.",
        ]:
            label = QLabel(line)
            label.setWordWrap(True)
            self._dashboard_text_labels.append(label)
            notifications.body_layout.addWidget(label)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        right_layout.addWidget(attendance)
        right_layout.addWidget(tasks)
        right_layout.addWidget(notifications)

        main_grid.addWidget(production, 0, 0)
        main_grid.addWidget(right_column, 0, 1)
        main_grid.setColumnStretch(0, 2)
        main_grid.setColumnStretch(1, 1)
        layout.addLayout(main_grid, 1)

        return content

    def _make_chart_placeholder(self, summary: dict[str, str]) -> QWidget:
        area = QFrame()
        self._chart_area = area
        area.setMinimumHeight(300)

        layout = QVBoxLayout(area)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        bars = QHBoxLayout()
        bars.setSpacing(14)
        metrics = [
            ("Aktif", hris_summary_int(summary, "active_employees")),
            ("Assign", hris_summary_int(summary, "active_assignments")),
            ("Payroll", hris_summary_int(summary, "payroll_profiles")),
            ("BPJS", hris_summary_int(summary, "bpjs_health_active")),
            ("Dok", hris_summary_int(summary, "document_count")),
            ("Move", hris_summary_int(summary, "movements_30d")),
            ("QA", hris_summary_int(summary, "quality_open_total")),
        ]
        max_value = max((value for _label, value in metrics), default=1) or 1

        bar_row = QHBoxLayout()
        bar_row.setSpacing(14)
        for label_text, value in metrics:
            col = QVBoxLayout()
            col.setSpacing(6)
            col.addStretch(1)
            bar = QFrame()
            bar.setFixedWidth(34)
            height = max(18, round((value / max_value) * 230))
            bar.setFixedHeight(height)
            bar.setStyleSheet("QFrame { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5BA4F0, stop:1 #1C67C7); border-radius: 6px; }")
            month_label = QLabel(label_text)
            month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._dashboard_text_labels.append(month_label)
            col.addWidget(bar, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            col.addWidget(month_label)
            bar_row.addLayout(col)
        bars.addLayout(bar_row)
        bars.addStretch(1)

        trend = QLabel(
            f"Kelengkapan {summary['data_completeness']} | QA {summary['data_quality_score']} | "
            f"Movement 30 hari {summary['movements_30d']}."
        )
        self._dashboard_text_labels.append(trend)

        layout.addStretch(1)
        layout.addLayout(bars)
        layout.addWidget(trend)
        return area

    def _make_attendance_placeholder(self, summary: dict[str, str]) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        present = hris_summary_int(summary, "attendance_present_today")
        exception = hris_summary_int(summary, "attendance_exception_today")
        total = hris_summary_int(summary, "attendance_today")
        if total <= 0:
            total = present + exception
        absent = max(total - present - exception, 0)

        pie = QLabel(f"{present}\nHadir")
        pie.setFixedSize(180, 180)
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pie.setStyleSheet(
            "QLabel { background: qconicalgradient(cx:0.5, cy:0.5, angle:0, stop:0 #5BAE44, stop:0.72 #5BAE44, stop:0.72 #F0C84B, stop:0.90 #F0C84B, stop:0.90 #D94A38, stop:1 #D94A38);"
            "border-radius: 90px; color: white; font-size: 26px; font-weight: 800; }"
        )

        legend = QVBoxLayout()
        for color, label_text in [
            ("#5BAE44", f"Hadir {present}"),
            ("#F0C84B", f"Izin/Sakit/Cuti {exception}"),
            ("#D94A38", f"Belum tercatat {absent}"),
        ]:
            row = QHBoxLayout()
            dot = QLabel()
            dot.setFixedSize(16, 16)
            dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
            label = QLabel(label_text)
            self._dashboard_text_labels.append(label)
            row.addWidget(dot)
            row.addWidget(label)
            row.addStretch(1)
            legend.addLayout(row)
        legend.addStretch(1)

        layout.addWidget(pie)
        layout.addLayout(legend)
        return wrapper

    def _make_task_row(self, task_text: str, badge_text: str, badge_color: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        task = QLabel(f"✔ {task_text}")
        self._dashboard_text_labels.append(task)

        badge = QLabel(badge_text)
        badge.setProperty("badgeColor", badge_color)
        self._dashboard_badges.append(badge)

        layout.addWidget(task)
        layout.addStretch(1)
        layout.addWidget(badge)
        return row

    def _build_footer(self) -> QWidget:
        footer = LoginGlassPanel(5.0)
        self._glass_panels.append(footer)
        footer.setFixedHeight(42)
        footer.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(14, 0, 14, 0)
        self._footer_label = QLabel("© 2026 Sistem Kebun  |  Versi 1.0")
        self._footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._footer_label)
        return footer

    def _update_charging_theme(self) -> None:
        charging = _resolve_charging_state(_get_battery_info())
        if self._charging == charging:
            return
        self._charging = charging
        self._apply_dashboard_theme(charging)

    def _apply_dashboard_theme(self, charging: bool) -> None:
        palette = _charging_theme_palette(charging)
        self._root_background.set_charging(charging)
        for panel in self._glass_panels:
            panel.set_charging(charging)
        for item in self._nav_items.values():
            item.set_charging(charging)
        for card in self._info_cards:
            card.set_charging(charging)
        for card in self._section_cards:
            card.set_charging(charging)
        for button in self._action_buttons:
            button.set_charging(charging)

        header_css = f"color: {palette['panel_text']}; background: transparent;"
        if self._header_brand is not None:
            self._header_brand.setStyleSheet(header_css + "font-size: 16px; font-weight: 850;")
        if self._header_title is not None:
            self._header_title.setStyleSheet(header_css + "font-size: 22px; font-weight: 850;")
        if self._header_user_info is not None:
            self._header_user_info.setStyleSheet(
                f"color: {palette['panel_muted']}; background: transparent; font-size: 12px; font-weight: 650;"
            )
        if self._header_mode_badge is not None:
            self._header_mode_badge.setText(palette["badge_label"])
            self._header_mode_badge.setStyleSheet(
                "QLabel {"
                f" background: {palette['badge_bg']}; color: {palette['badge_text']};"
                f" border: 1px solid {palette['badge_border']};"
                " border-radius: 11px; font-size: 11px; font-weight: 850;"
                "}"
            )
        if self._page_title_label is not None:
            self._page_title_label.setStyleSheet(
                f"color: {palette['panel_text']}; font-size: 38px; font-weight: 850; background: transparent;"
            )
        for title_label in self._page_title_labels:
            title_label.setStyleSheet(
                f"color: {palette['panel_text']}; font-size: 38px; font-weight: 850; background: transparent;"
            )
        if self._footer_label is not None:
            self._footer_label.setStyleSheet(
                f"color: {palette['panel_muted']}; font-size: 13px; font-weight: 750; background: transparent;"
            )
        if self._chart_area is not None:
            self._chart_area.setStyleSheet(
                "QFrame {"
                f" background: {palette['surface_bg']};"
                f" border: 1px solid {palette['panel_border']};"
                " border-radius: 12px;"
                "}"
            )

        for label in self._dashboard_text_labels:
            is_trend = "Produksi bulanan" in label.text()
            label.setStyleSheet(
                (
                    "color: #7CE38A; font-size: 13px; font-weight: 800; background: transparent;"
                    if is_trend
                    else f"color: {palette['panel_text']}; font-size: 13px; font-weight: 700; background: transparent;"
                )
            )

        for label in self._dashboard_muted_labels:
            label.setStyleSheet(
                f"color: {palette['panel_muted']}; font-size: 12px; font-weight: 650; background: transparent;"
            )

        for badge in self._dashboard_badges:
            source_color = str(badge.property("badgeColor") or palette["surface_selected"])
            badge_bg = "rgba(80, 180, 255, 0.18)" if charging else "rgba(255, 255, 255, 0.13)"
            badge_border = palette["panel_border"]
            if source_color in {"#F7D7D6", "#F6EEBD"}:
                badge_bg = "rgba(255, 255, 255, 0.16)" if not charging else "rgba(126, 232, 255, 0.13)"
            badge.setStyleSheet(
                f"background: {badge_bg}; color: {palette['panel_text']}; border: 1px solid {badge_border};"
                " border-radius: 8px; padding: 5px 10px; font-size: 12px; font-weight: 800;"
            )

        field_style = (
            "QLineEdit, QComboBox {"
            f" background: {palette['surface_bg']};"
            f" color: {palette['panel_text']};"
            f" border: 1px solid {palette['panel_border']};"
            " border-radius: 9px; padding: 0 12px; font-size: 14px; font-weight: 650;"
            "}"
            "QLineEdit::placeholder { color: rgba(230, 237, 246, 0.46); }"
            "QComboBox::drop-down { border: none; width: 24px; }"
        )
        if self._search_username is not None:
            self._search_username.setStyleSheet(field_style)
        if self._role_filter is not None:
            self._role_filter.setStyleSheet(field_style)
        if self._hris_quality_search is not None:
            self._hris_quality_search.setStyleSheet(field_style)
        if self._hris_quality_status_filter is not None:
            self._hris_quality_status_filter.setStyleSheet(field_style)
        if self._hris_quality_severity_filter is not None:
            self._hris_quality_severity_filter.setStyleSheet(field_style)
        if self._add_user_btn is not None:
            self._add_user_btn.setStyleSheet(
                "QPushButton {"
                f" background: {palette['surface_selected']}; color: {palette['panel_text']};"
                f" border: 1px solid {palette['panel_border']};"
                " border-radius: 9px; padding: 0 16px; font-size: 14px; font-weight: 800;"
                "}"
                f"QPushButton:hover {{ background: {palette['surface_hover']}; }}"
                f"QPushButton:pressed {{ background: {palette['surface_selected']}; }}"
            )
        table_style = (
            "QTableWidget {"
            f" background: {palette['table_bg']}; alternate-background-color: {palette['table_alt']};"
            f" color: {palette['panel_text']}; border: 1px solid {palette['panel_border']};"
            " border-radius: 12px; font-size: 14px; outline: none;"
            "}"
            "QHeaderView::section {"
            f" background: {palette['table_header']}; color: {palette['panel_muted']};"
            " font-size: 11px; font-weight: 800; border: none; border-bottom: 1px solid rgba(255,255,255,0.18); padding: 10px 14px;"
            "}"
            "QTableWidget::item { padding: 10px 12px; border: none; }"
            f"QTableWidget::item:hover {{ background: {palette['surface_hover']}; }}"
            f"QTableWidget::item:selected {{ background: {palette['surface_selected']}; color: {palette['panel_text']}; }}"
        )
        if self._users_table is not None:
            self._users_table.setStyleSheet(table_style)
            self._sync_user_table_widget_states()
        if self._hris_quality_table is not None:
            self._hris_quality_table.setStyleSheet(table_style)
        if self._hris_quality_refresh_btn is not None:
            self._hris_quality_refresh_btn.setStyleSheet(
                "QPushButton {"
                f" background: {palette['surface_selected']}; color: {palette['panel_text']};"
                f" border: 1px solid {palette['panel_border']};"
                " border-radius: 8px; font-size: 13px; font-weight: 800;"
                "}"
                f"QPushButton:hover {{ background: {palette['surface_hover']}; }}"
                f"QPushButton:pressed {{ background: {palette['surface_selected']}; }}"
            )
        quality_button_style = (
            "QPushButton {"
            f" background: {palette['surface_selected']}; color: {palette['panel_text']};"
            f" border: 1px solid {palette['panel_border']};"
            " border-radius: 8px; padding: 0 12px; font-size: 13px; font-weight: 800;"
            "}"
            f"QPushButton:hover {{ background: {palette['surface_hover']}; }}"
            f"QPushButton:pressed {{ background: {palette['surface_selected']}; }}"
            "QPushButton:disabled { background: rgba(255, 255, 255, 0.08); color: rgba(244, 248, 255, 0.44); }"
        )
        for button in self._hris_quality_action_buttons:
            button.setStyleSheet(quality_button_style)


def show_dashboard(app: QApplication, user: Optional[User] = None) -> DashboardForm:
    global _active_dashboard
    if _active_dashboard is not None and _active_dashboard.isVisible():
        current_user_id = _active_dashboard.current_user_id()
        incoming_user_id = int(getattr(user, "id", 0) or 0)

        # If login user changed, rebuild dashboard to avoid stale permissions/user context.
        if incoming_user_id > 0 and incoming_user_id != current_user_id:
            _active_dashboard.close()
            _active_dashboard.deleteLater()
            _active_dashboard = None
        else:
            _active_dashboard.raise_()
            _active_dashboard.activateWindow()
            return _active_dashboard

    _active_dashboard = DashboardForm(user=user)
    _active_dashboard.showMaximized()
    _active_dashboard.raise_()
    _active_dashboard.activateWindow()
    return _active_dashboard
