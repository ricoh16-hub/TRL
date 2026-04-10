from datetime import date, datetime
import secrets
import string
from typing import Optional, TypedDict, cast

from PySide6.QtCore import Property, QEvent, QPropertyAnimation, QEasingCurve, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QEnterEvent, QKeyEvent, QMouseEvent
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

_active_dashboard: Optional["DashboardForm"] = None

NAVY_TOP = "#163A69"
NAVY_SIDE = "#1C467A"
NAVY_SELECTED = "#244F89"
PAGE_BG = "#EFF3F8"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#22324A"
TEXT_SOFT = "#70829A"

TEMP_PASSWORD_LENGTH = 12
CHARGING_ACCENT = "#50B4FF"


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
    return bool(info.get("charging")) if info else False


def _charging_theme_palette(charging: bool) -> dict[str, str]:
    if charging:
        return {
            "accent": CHARGING_ACCENT,
            "hover": "#3AA8F5",
            "pressed": "#2A96E0",
            "badge_bg": "rgba(80, 180, 255, 0.14)",
            "badge_border": "rgba(80, 180, 255, 0.34)",
            "badge_text": CHARGING_ACCENT,
            "badge_label": "Charging Mode",
        }
    return {
        "accent": NAVY_TOP,
        "hover": NAVY_SELECTED,
        "pressed": "#0e2847",
        "badge_bg": "rgba(22, 58, 105, 0.08)",
        "badge_border": "rgba(22, 58, 105, 0.18)",
        "badge_text": NAVY_TOP,
        "badge_label": "Standard Mode",
    }


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
        if self._active:
            pad = 18 + int(depth)
            self.setStyleSheet(
                f"background: {NAVY_SELECTED}; color: white; font-size: 14px; font-weight: 800;"
                f"border-left: 4px solid #FFFFFF; padding-left: {pad}px;"
            )
            return

        alpha = int((70 * self._hover_progress) + (35 * self._press_progress))
        pad = 22 + int(depth)
        self.setStyleSheet(
            "color: white; font-size: 14px; font-weight: 600;"
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
        self.setStyleSheet(
            f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )
        self.setMinimumHeight(120)

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


class AnimatedSectionCard(AnimatedHoverCard):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 14px; font-weight: 800;")
        layout.addWidget(title_label)
        self.body_layout = layout


class AnimatedActionButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self._hover_progress = 0.0
        self._press_progress = 0.0

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
        self._apply_style()

    def _apply_style(self) -> None:
        darken = int((28 * self._hover_progress) + (52 * self._press_progress))
        r = max(140, 217 - darken)
        g = max(40, 74 - darken)
        b = max(30, 56 - darken)
        self.setStyleSheet(
            f"QPushButton {{ background: rgb({r}, {g}, {b}); color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; }}"
        )

        blur = 16 + (8 * self._hover_progress)
        offset = 3 + (2 * self._hover_progress)
        alpha = 120 + int(45 * self._hover_progress)
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(0, offset)
        self._shadow.setColor(QColor(120, 35, 25, alpha))

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


class ChangePasswordDialog(QDialog):
    """Dialog untuk mengganti password dan PIN user sendiri"""

    def __init__(self, username: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ganti Password")
        self.setModal(True)
        self.resize(420, 280)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        title = QLabel(f"Ganti Password dan PIN\nUser: {username}")
        title.setStyleSheet(f"color: {TEXT_DARK}; font-size: 14px; font-weight: 700;")
        layout.addWidget(title)

        self._old_password_input = QLineEdit()
        self._old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_password_input.setPlaceholderText("Masukkan password lama")

        self._new_password_input = QLineEdit()
        self._new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_password_input.setPlaceholderText("Masukkan password baru")

        self._old_pin_input = QLineEdit()
        self._old_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._old_pin_input.setPlaceholderText("Masukkan PIN lama (6 digit)")
        self._old_pin_input.setMaxLength(6)

        self._new_pin_input = QLineEdit()
        self._new_pin_input.setEchoMode(QLineEdit.EchoMode.Password)
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

    def data(self) -> dict[str, str]:
        return {
            "old_password": self._old_password_input.text(),
            "new_password": self._new_password_input.text(),
            "old_pin": self._old_pin_input.text().strip(),
            "new_pin": self._new_pin_input.text().strip(),
        }


class UserEditDialog(QDialog):
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
        super().__init__(parent)
        self.setWindowTitle("Edit User")
        self.setModal(True)
        self.resize(520, 660)
        self._charging: Optional[bool] = None

        self.setStyleSheet(f"QDialog {{ background: {PAGE_BG}; }}")

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

        header_label = QLabel("Edit User")
        header_label.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 18px; font-weight: 900;"
        )
        header_subtitle = QLabel(
            "Manage profile details, existing credentials, and access updates in one panel."
        )
        header_subtitle.setWordWrap(True)
        header_subtitle.setStyleSheet(
            f"color: {TEXT_SOFT}; font-size: 12px; font-weight: 500;"
        )
        header_block.addWidget(header_label)
        header_block.addWidget(header_subtitle)

        self._theme_badge = QLabel("Standard Mode")
        self._theme_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._theme_badge.setMinimumWidth(118)
        self._theme_badge.setFixedHeight(30)

        header_row.addLayout(header_block, 1)
        header_row.addWidget(self._theme_badge, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(header_row)

        # --- Section: User Information ---
        info_card = QFrame()
        info_card.setStyleSheet(
              f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )
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
        try:
            normalized_role = normalize_role_name(role)
        except ValueError:
            normalized_role = "Operator"
        self._role_combo.setCurrentText(normalized_role)
        self._status_combo = QComboBox()
        self._status_combo.addItems(["Active", "Inactive"])
        self._status_combo.setFixedHeight(36)
        self._status_combo.setStyleSheet(self._combo_style())
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

        # --- Section: Current Credentials ---
        old_card = QFrame()
        old_card.setStyleSheet(
              f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )
        _apply_card_shadow(old_card)
        old_inner = QVBoxLayout(old_card)
        old_inner.setContentsMargins(20, 14, 20, 14)
        old_inner.setSpacing(10)

        self._old_title = QLabel("Current Credentials")
        self._old_title.setStyleSheet(
            f"color: {NAVY_TOP}; font-size: 12px; font-weight: 800;"
            " border: none; background: transparent;"
        )
        old_inner.addWidget(self._old_title)

        old_form = QFormLayout()
        old_form.setSpacing(8)
        self._old_password_input = self._make_field()
        self._old_password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self._old_password_input.setPlaceholderText("Enter current password to change it")
        if current_password:
            self._old_password_input.setText(current_password)
        self._old_pin_input = self._make_field()
        self._old_pin_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self._old_pin_input.setPlaceholderText("Current PIN (6 digits)")
        self._old_pin_input.setMaxLength(6)
        if current_pin:
            self._old_pin_input.setText(current_pin)
        old_form.addRow(self._row_label("Current Password"), self._old_password_input)
        old_form.addRow(self._row_label("Current PIN"), self._old_pin_input)
        old_inner.addLayout(old_form)
        old_hint = QLabel("Shown as-is to speed up verification and credential rotation.")
        old_hint.setWordWrap(True)
        old_hint.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 11px;")
        old_inner.addWidget(old_hint)
        main_layout.addWidget(old_card)

        # --- Section: New Credentials ---
        new_card = QFrame()
        new_card.setStyleSheet(
              f"QFrame {{ background: {CARD_BG}; border-radius: 12px; border: 1px solid #DEE6F0; }}"
        )
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
        new_hint.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 11px;")
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
        self._btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {PAGE_BG};
                color: {TEXT_DARK};
                border: 1.5px solid #DEE6F0;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: #DEE6F0; }}
        """)
        self._btn_cancel.clicked.connect(self.reject)

        self._btn_save = QPushButton("Save Changes")
        self._btn_save.setFixedHeight(40)
        self._btn_save.setMinimumWidth(140)
        self._btn_save.setStyleSheet(
            self._save_btn_style(NAVY_TOP, NAVY_SELECTED, "#0e2847")
        )
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
        lbl.setStyleSheet(
            f"color: {TEXT_SOFT}; font-size: 12px; font-weight: 600;"
            " border: none; background: transparent;"
        )
        return lbl

    def _make_field(self, text: str = "") -> QLineEdit:
        inp = QLineEdit(text)
        inp.setFixedHeight(36)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background: {CARD_BG};
                border: 1.5px solid #DEE6F0;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 13px;
                color: {TEXT_DARK};
            }}
            QLineEdit:focus {{
                border: 1.5px solid {NAVY_SELECTED};
                background: #F8FAFD;
            }}
        """)
        return inp

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {CARD_BG};
                border: 1.5px solid #DEE6F0;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 13px;
                color: {TEXT_DARK};
            }}
            QComboBox:focus {{
                border: 1.5px solid {NAVY_SELECTED};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """

    def _save_btn_style(self, bg: str, hover: str, pressed: str) -> str:
        return f"""
            QPushButton {{
                background: {bg};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
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
        info = _get_battery_info()
        charging = _resolve_charging_state(info)
        if charging == self._charging:
            return
        self._charging = charging
        palette = _charging_theme_palette(charging)
        accent = palette["accent"]
        self._header_bar.setStyleSheet(
            f"background: {accent}; border-radius: 2px;"
        )
        title_css = (
            f"color: {accent}; font-size: 12px; font-weight: 800;"
            " border: none; background: transparent;"
        )
        self._info_title.setStyleSheet(title_css)
        self._old_title.setStyleSheet(title_css)
        self._new_title.setStyleSheet(title_css)
        self._theme_badge.setText(palette["badge_label"])
        self._theme_badge.setStyleSheet(
            self._badge_style(
                palette["badge_bg"],
                palette["badge_border"],
                palette["badge_text"],
            )
        )
        self._btn_save.setStyleSheet(
            self._save_btn_style(accent, palette["hover"], palette["pressed"])
        )

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


class UserAddDialog(QDialog):
    """Dialog to add a new user (password and PIN are auto-generated)."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add User")
        self.setModal(True)
        self.resize(420, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Example: riko01")
        
        self._nama_input = QLineEdit()
        self._nama_input.setPlaceholderText("Example: Riko Sinaga")
        
        self._role_combo = QComboBox()
        self._role_combo.addItems(list(CANONICAL_ROLES))
        self._role_combo.setCurrentText("Operator")
        
        self._status_combo = QComboBox()
        self._status_combo.addItems(["Active", "Inactive"])

        form.addRow("Username", self._username_input)
        form.addRow("Full Name", self._nama_input)
        form.addRow("Role", self._role_combo)
        form.addRow("Status", self._status_combo)
        layout.addLayout(form)
        
        info_label = QLabel("Password and PIN will be generated automatically.")
        info_label.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 12px; font-style: italic;")
        layout.addWidget(info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        self._nav_items: dict[str, AnimatedNavItem] = {}
        self._users_table: Optional[QTableWidget] = None
        self._search_username: Optional[QLineEdit] = None
        self._role_filter: Optional[QComboBox] = None
        self._all_users_rows: list[UserRow] = []
        self.setWindowTitle("Dashboard")
        self.resize(1360, 820)
        self.setMinimumSize(960, 600)

        root = QWidget(self)
        root.setStyleSheet(f"background: {PAGE_BG};")
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

    def current_user_id(self) -> int:
        return int(getattr(self._user, "id", 0) or 0)

    def _build_temp_password(self, length: int = TEMP_PASSWORD_LENGTH) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _build_content_stack(self) -> QWidget:
        self._content_stack = QStackedWidget()
        self._dashboard_overview_page = self._build_content()
        self._management_user_page = self._build_management_users_page()
        self._content_stack.addWidget(self._dashboard_overview_page)
        self._content_stack.addWidget(self._management_user_page)
        self._content_stack.setCurrentWidget(self._dashboard_overview_page)
        return self._content_stack

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(88)
        header.setStyleSheet(f"background: {NAVY_TOP};")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 10, 22, 10)
        layout.setSpacing(16)

        brand = QLabel("🌴  SISTEM KEBUN SAWIT")
        brand.setStyleSheet("color: white; font-size: 16px; font-weight: 800;")

        title = QLabel("Dashboard Utama")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; font-size: 22px; font-weight: 800;")

        username = self._user.username if self._user is not None else "User"
        raw_role = str(getattr(self._user, "role", "Operator") or "Operator") if self._user is not None else "Operator"
        try:
            role = normalize_role_name(raw_role)
        except ValueError:
            role = raw_role
        date_text = date.today().strftime("%d %B %Y")
        user_info = QLabel(f"User: {username}  |  Level: {role}\nTanggal: {date_text}")
        user_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        user_info.setStyleSheet("color: white; font-size: 12px; font-weight: 600;")

        change_password_btn = AnimatedActionButton("Ganti Password")
        change_password_btn.setFixedSize(140, 40)
        change_password_btn.clicked.connect(self._open_change_password_dialog)

        logout_btn = AnimatedActionButton("Logout")
        logout_btn.setFixedSize(108, 40)
        logout_btn.clicked.connect(self.close)

        layout.addWidget(brand)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(user_info)
        layout.addWidget(change_password_btn)
        layout.addWidget(logout_btn)
        return header

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(265)
        sidebar.setStyleSheet(f"background: {NAVY_SIDE};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 18, 0, 18)
        layout.setSpacing(10)

        menu_items = [
            ("dashboard", "Dashboard"),
            ("data_master", "Data Master"),
            ("data_karyawan", "Data Karyawan"),
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

        self._content_stack.setCurrentWidget(self._dashboard_overview_page)

    def _build_management_users_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("User Management")
        title.setStyleSheet(f"color: {TEXT_DARK}; font-size: 38px; font-weight: 800;")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._search_username = QLineEdit()
        self._search_username.setPlaceholderText("Search username...")
        self._search_username.setFixedHeight(36)
        self._search_username.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid #D7E0EA; border-radius: 8px; padding: 0 12px; font-size: 14px; }"
        )
        self._search_username.textChanged.connect(self._apply_user_filters)

        filter_label = QLabel("Role Filter")
        filter_label.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 14px; font-weight: 700;")

        self._role_filter = QComboBox()
        self._role_filter.addItem("All")
        self._role_filter.setFixedHeight(36)
        self._role_filter.setMinimumWidth(180)
        self._role_filter.setStyleSheet(
            "QComboBox { background: white; border: 1px solid #D7E0EA; border-radius: 8px; padding: 0 10px; font-size: 14px; }"
        )
        self._role_filter.currentTextChanged.connect(self._apply_user_filters)

        add_user_btn = QPushButton("+ Add User")
        add_user_btn.setFixedHeight(36)
        add_user_btn.setMinimumWidth(140)
        add_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_user_btn.setStyleSheet(
            "QPushButton { background: #2559A6; color: white; border: none; border-radius: 8px; padding: 0 16px; font-size: 14px; font-weight: 700; }"
            "QPushButton:hover { background: #1E4681; }"
            "QPushButton:pressed { background: #163A58; }"
        )
        add_user_btn.clicked.connect(self._open_add_user_dialog)

        controls.addWidget(self._search_username, 2)
        controls.addStretch(1)
        controls.addWidget(filter_label)
        controls.addWidget(self._role_filter)
        controls.addWidget(add_user_btn)
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
            "QTableWidget { background: white; alternate-background-color: #F5F9FF; border: 1px solid #D5E2F0; border-radius: 12px; font-size: 14px; outline: none; }"
            "QHeaderView::section { background: #EDF3FB; color: #6B87A8; font-size: 11px; font-weight: 700; border: none; border-bottom: 2px solid #DAE6F3; padding: 10px 14px; }"
            "QTableWidget::item { padding: 10px 12px; color: #2D405C; border: none; }"
            "QTableWidget::item:hover { background: #EDF5FF; }"
            "QTableWidget::item:selected { background: #DDEEFF; color: #163A69; }"
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
        if is_active:
            if selected:
                pill.setStyleSheet("background: #DDEFE5; border: 1px solid #B7CCBE; border-radius: 12px;")
                dot.setStyleSheet("QLabel { background: #1F8F55; border-radius: 4px; border: none; }")
            else:
                pill.setStyleSheet("background: #E8F4EE; border: 1px solid #C9D8CE; border-radius: 12px;")
                dot.setStyleSheet("QLabel { background: #22A15F; border-radius: 4px; border: none; }")
            lbl.setStyleSheet(
                "QLabel { color: #1F6B45; font-size: 12px; font-weight: 700; background: transparent; border: none; }"
            )
        else:
            if selected:
                pill.setStyleSheet("background: #F3E2E2; border: 1px solid #CFB8B8; border-radius: 12px;")
                dot.setStyleSheet("QLabel { background: #C74747; border-radius: 4px; border: none; }")
            else:
                pill.setStyleSheet("background: #F8ECEC; border: 1px solid #DCCACA; border-radius: 12px;")
                dot.setStyleSheet("QLabel { background: #D65353; border-radius: 4px; border: none; }")
            lbl.setStyleSheet(
                "QLabel { color: #8D2F2F; font-size: 12px; font-weight: 700; background: transparent; border: none; }"
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
                pass

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
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #D0DAE7; border-radius: 8px; padding: 4px; font-size: 13px; }"
            "QMenu::item { padding: 7px 20px; border-radius: 5px; color: #2D405C; }"
            "QMenu::item:selected { background: #E7F1FF; color: #1F3F66; }"
            "QMenu::separator { height: 1px; background: #E7EDF4; margin: 3px 8px; }"
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
            password_plaintext = str(getattr(user, "password_plaintext", None) or "").strip()
            pin_plaintext = str(getattr(user, "pin_plaintext", None) or "").strip()
            row: UserRow = {
                "id": user_id,
                "username": username,
                "full_name": full_name or username.replace("_", " ").title(),
                "email": email or "-",
                "phone": phone or "-",
                "role": normalized_role,
                "status": "Active" if status in {"aktif", "active"} else "Inactive",
                "password_value": password_plaintext if password_plaintext else ("✓ CONFIGURED" if getattr(password_record, "password_hash", None) else "-"),
                "pin_value": pin_plaintext if pin_plaintext else ("✓ CONFIGURED" if getattr(pin_record, "pin_hash", None) else "-"),
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
            edit_btn.setFixedSize(102, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(
                "QPushButton { background: #2563EB; color: white; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: #1D55D8; }"
                "QPushButton:pressed { background: #1749C0; }"
                "QPushButton:disabled { background: #BFCDE2; color: #6A7F9E; }"
            )
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
            more_btn.setFixedSize(38, 28)
            more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            more_btn.setStyleSheet(
                "QPushButton { background: #FFFFFF; color: #3F5875; border: 1px solid #CDDAEA; border-radius: 6px; font-size: 13px; font-weight: 800; padding: 0; }"
                "QPushButton:hover { background: #EEF3FA; color: #22364D; border-color: #B8CAE0; }"
                "QPushButton:pressed { background: #E2EBF5; }"
            )
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
            user = session.get(User, user_id)
            if user is None:
                QMessageBox.warning(self, "Data Not Found", "User not found.")
                return

            raw_role = str(getattr(user, "role", "") or "").strip()
            role_value = raw_role if raw_role else fallback_role

            raw_status = str(getattr(user, "status", "") or "").strip()
            status_value = raw_status if raw_status else fallback_status

            raw_password = str(getattr(user, "password_plaintext", "") or "").strip()
            password_value = raw_password if raw_password else fallback_password
            if password_value in {"-", "✓ CONFIGURED"}:
                password_value = ""

            raw_pin = str(getattr(user, "pin_plaintext", "") or "").strip()
            pin_value = raw_pin if raw_pin else fallback_pin
            if pin_value in {"-", "✓ CONFIGURED"}:
                pin_value = ""

            dialog = UserEditDialog(
                username=str(getattr(user, "username", "") or ""),
                nama=str(getattr(user, "nama", "") or ""),
                role=role_value,
                status=status_value,
                current_password=password_value,
                current_pin=pin_value,
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            payload = dialog.data()
            if not payload["username"]:
                QMessageBox.warning(self, "Validation", "Username cannot be empty.")
                return

            old_password = str(payload.get("old_password", "") or "")
            new_password = str(payload.get("new_password", "") or "")
            old_pin = str(payload.get("old_pin", "") or "")
            new_pin = str(payload.get("new_pin", "") or "")

            if new_password and not old_password:
                QMessageBox.warning(self, "Validation", "Enter current password to change password.")
                return

            if new_pin and not old_pin:
                QMessageBox.warning(self, "Validation", "Enter current PIN to change PIN.")
                return

            if new_password:
                password_record = getattr(user, "password_record", None)
                stored_salt = str(getattr(password_record, "password_salt", "") or "")
                stored_hash = str(getattr(password_record, "password_hash", "") or "")
                if not stored_salt or not stored_hash:
                    QMessageBox.warning(self, "Validation", "Current password is not available for this user.")
                    return
                if not verify_password(old_password, stored_salt, stored_hash):
                    QMessageBox.warning(self, "Validation", "Current password is incorrect.")
                    return

            if new_pin:
                pin_record = getattr(user, "pin_record", None)
                stored_pin_salt = str(getattr(pin_record, "pin_salt", "") or "")
                stored_pin_hash = str(getattr(pin_record, "pin_hash", "") or "")
                if not stored_pin_salt or not stored_pin_hash:
                    QMessageBox.warning(self, "Validation", "Current PIN is not available for this user.")
                    return
                if not verify_pin_code(old_pin, stored_pin_salt, stored_pin_hash):
                    QMessageBox.warning(self, "Validation", "Current PIN is incorrect.")
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
            QMessageBox.warning(self, "Validation", str(error))
            return
        finally:
            session.close()

        self._load_users_table()

    def _get_current_user_access_profile(self) -> tuple[str, str]:
        if self._user is None:
            return ("Unknown", "Inactive")

        # Always read latest role/status from DB to avoid stale in-memory user state.
        user_id = int(getattr(self._user, "id", 0) or 0)
        if user_id > 0:
            session = Session()
            try:
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

    def _can_current_user_edit_users(self) -> bool:
        # Backward-compatible alias for existing call sites.
        return self._can_current_user_manage_user_actions()

    def _show_user_action_access_denied_dialog(self, action_name: str) -> None:
        role_value, status_value = self._get_current_user_access_profile()
        dialog = QDialog(self)
        dialog.setModal(True)
        dialog.setWindowTitle("User Action Restricted")
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            | Qt.WindowType.WindowCloseButtonHint
        )
        dialog.setFixedWidth(464)
        dialog.setStyleSheet(
            "QDialog {"
            " background: #F6F9FD;"
            " border: 1px solid #D9E2EF;"
            " border-radius: 0px;"
            "}"
            "QFrame#headerBand {"
            " background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EEF3FB, stop:1 #E8F0FC);"
            " border: 1px solid #D5E0EE;"
            " border-radius: 8px;"
            "}"
            "QLabel#titleLabel { color: #1E3E67; font-size: 14px; font-weight: 800; }"
            "QLabel#subtitleLabel { color: #4A678A; font-size: 11px; font-weight: 600; }"
            "QFrame#contentCard {"
            " background: rgba(255, 255, 255, 0.92);"
            " border: 1px solid #D9E3F2;"
            " border-radius: 8px;"
            "}"
            "QLabel#infoIcon {"
            " min-width: 28px; max-width: 28px;"
            " min-height: 28px; max-height: 28px;"
            " border-radius: 14px;"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2C8ED8, stop:1 #1E71BB);"
            " color: white;"
            " font-size: 15px;"
            " font-weight: 900;"
            " qproperty-alignment: AlignCenter;"
            "}"
            "QLabel#contentText { color: #284566; font-size: 11px; }"
            "QLabel#statusPill {"
            " color: #1B4B78;"
            " background: #ECF3FF;"
            " border: 1px solid #CCDCF3;"
            " border-radius: 8px;"
            " padding: 3px 8px;"
            " font-size: 10px;"
            " font-weight: 700;"
            "}"
        )

        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(7)

        header_band = QFrame()
        header_band.setObjectName("headerBand")
        header_layout = QVBoxLayout(header_band)
        header_layout.setContentsMargins(9, 6, 9, 6)
        header_layout.setSpacing(1)
        title = QLabel("User Action Restricted")
        title.setObjectName("titleLabel")
        subtitle = QLabel(f"Action blocked: {action_name} in User Management")
        subtitle.setObjectName("subtitleLabel")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root_layout.addWidget(header_band)

        content_card = QFrame()
        content_card.setObjectName("contentCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(10, 9, 10, 9)
        content_layout.setSpacing(6)

        content_top = QHBoxLayout()
        content_top.setSpacing(9)
        info_icon = QLabel("i")
        info_icon.setObjectName("infoIcon")
        content_text = QLabel(
            "You are not allowed to perform this action.\n"
            "Only users with Role = Superior and Status = Active can perform Edit and Delete actions.\n"
            "Please contact an Active Superior for assistance."
        )
        content_text.setObjectName("contentText")
        content_text.setWordWrap(True)
        content_text.setMinimumWidth(370)
        content_text.setMaximumWidth(370)
        content_text.adjustSize()
        content_text.setMinimumHeight(content_text.sizeHint().height() + 6)
        content_top.addWidget(info_icon, alignment=Qt.AlignmentFlag.AlignTop)
        content_top.addWidget(content_text, stretch=1)
        content_layout.addLayout(content_top)

        access_row = QHBoxLayout()
        role_pill = QLabel(f"Role: {role_value}")
        role_pill.setObjectName("statusPill")
        status_pill = QLabel(f"Status: {status_value}")
        status_pill.setObjectName("statusPill")
        access_row.addWidget(role_pill)
        access_row.addWidget(status_pill)
        access_row.addStretch()
        content_layout.addLayout(access_row)
        root_layout.addWidget(content_card)

        required_height = max(220, content_text.sizeHint().height() + 150)
        dialog.setFixedHeight(required_height)

        if self.isVisible():
            center = self.frameGeometry().center()
            dialog_rect = dialog.frameGeometry()
            dialog_rect.moveCenter(center)
            dialog.move(dialog_rect.topLeft())

        dialog.exec()

    def _delete_user(self, user_id: int, username: str) -> None:
        if not self._can_current_user_manage_user_actions():
            self._show_user_action_access_denied_dialog("Delete")
            return

        answer = QMessageBox.question(
            self,
            "Delete User",
            f"Delete user '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        session = Session()
        try:
            delete_user(session, user_id)
        except ValueError as error:
            QMessageBox.warning(self, "Delete Failed", str(error))
            return
        finally:
            session.close()

        self._load_users_table()

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
        dialog = UserAddDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        data = dialog.data()
        
        # Validasi
        if not data["username"]:
            QMessageBox.warning(self, "Validation", "Username cannot be empty.")
            return
        
        if not data["nama"]:
            QMessageBox.warning(self, "Validation", "Full name cannot be empty.")
            return
        
        self._add_user(data)

    def _add_user(self, data: dict[str, str]) -> None:
        """Add a new user to the database with generated password and PIN."""
        # Generate password dan PIN
        generated_password = self._build_temp_password()
        generated_pin = "".join(secrets.choice(string.digits) for _ in range(6))
        
        session = Session()
        try:
            from database.crud import create_user
            
            user = create_user(
                session,
                username=data["username"],
                nama=data["nama"],
                password=generated_password,
                role=data["role"],
                status=data["status"],
            )
            
            # Set PIN untuk user baru
            created_user_id = int(getattr(user, "id", 0) or 0)
            set_user_pin(session, created_user_id, generated_pin)
            
            self._load_users_table()
            QMessageBox.information(
                self,
                "User Created",
                f"User '{data['username']}' was added successfully.\n\n"
                f"Password: {generated_password}\n"
                f"PIN: {generated_pin}\n\n"
                f"Save these credentials now (shown only once)."
            )
        except ValueError as error:
            QMessageBox.warning(self, "Validation", str(error))
            session.rollback()
            return
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Error: {error}")
            session.rollback()
            return
        finally:
            session.close()

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        top_cards = QGridLayout()
        top_cards.setHorizontalSpacing(16)
        top_cards.setVerticalSpacing(16)
        top_cards.addWidget(AnimatedInfoCard("🏭", "Total Produksi", "52,300 Kg", "#1D4ED8"), 0, 0)
        top_cards.addWidget(AnimatedInfoCard("✅", "Kehadiran Hari Ini", "85 Hadir", "#5BAE44"), 0, 1)
        top_cards.addWidget(AnimatedInfoCard("⚙", "Status Pekerjaan", "5 Tugas Berjalan", "#5BAE44"), 0, 2)
        top_cards.addWidget(AnimatedInfoCard("🔔", "Notifikasi", "2 Pesan Baru", "#D94A38"), 0, 3)
        layout.addLayout(top_cards)

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(16)
        main_grid.setVerticalSpacing(16)

        production = AnimatedSectionCard("Grafik Produksi")
        production.body_layout.addWidget(self._make_chart_placeholder())
        production.body_layout.addStretch(1)

        attendance = AnimatedSectionCard("Absensi Karyawan")
        attendance.body_layout.addWidget(self._make_attendance_placeholder())

        tasks = AnimatedSectionCard("Pekerjaan Hari Ini")
        for task_text, badge_text, badge_color in [
            ("Perawatan Blok A1", "Sedang Berlangsung", "#D7E8F8"),
            ("Panen Blok C3", "Dalam Proses", "#F7D7D6"),
            ("Penyemprotan Blok B2", "Belum Selesai", "#F6EEBD"),
        ]:
            tasks.body_layout.addWidget(self._make_task_row(task_text, badge_text, badge_color))

        notifications = AnimatedSectionCard("Notifikasi")
        for line in [
            "Pesan: Laporan harian sudah diupdate.",
            "Reminder: Rapat evaluasi jam 14.00.",
        ]:
            label = QLabel(line)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 13px; padding: 6px 0;")
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

    def _make_chart_placeholder(self) -> QWidget:
        area = QFrame()
        area.setMinimumHeight(300)
        area.setStyleSheet("QFrame { background: #F8FBFF; border: 1px solid #E1EAF3; border-radius: 10px; }")

        layout = QVBoxLayout(area)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        bars = QHBoxLayout()
        bars.setSpacing(14)
        heights = [90, 165, 150, 210, 176, 185, 230, 255, 170]
        months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep"]

        bar_row = QHBoxLayout()
        bar_row.setSpacing(14)
        for height, month in zip(heights, months):
            col = QVBoxLayout()
            col.setSpacing(6)
            col.addStretch(1)
            bar = QFrame()
            bar.setFixedWidth(34)
            bar.setFixedHeight(height)
            bar.setStyleSheet("QFrame { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5BA4F0, stop:1 #1C67C7); border-radius: 6px; }")
            month_label = QLabel(month)
            month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            month_label.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 11px;")
            col.addWidget(bar, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            col.addWidget(month_label)
            bar_row.addLayout(col)
        bars.addLayout(bar_row)
        bars.addStretch(1)

        trend = QLabel("Produksi bulanan meningkat stabil.")
        trend.setStyleSheet("color: #5BAE44; font-size: 13px; font-weight: 700;")

        layout.addStretch(1)
        layout.addLayout(bars)
        layout.addWidget(trend)
        return area

    def _make_attendance_placeholder(self) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        pie = QLabel("85\nHadir")
        pie.setFixedSize(180, 180)
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pie.setStyleSheet(
            "QLabel { background: qconicalgradient(cx:0.5, cy:0.5, angle:0, stop:0 #5BAE44, stop:0.72 #5BAE44, stop:0.72 #F0C84B, stop:0.90 #F0C84B, stop:0.90 #D94A38, stop:1 #D94A38);"
            "border-radius: 90px; color: white; font-size: 26px; font-weight: 800; }"
        )

        legend = QVBoxLayout()
        for color, text in [("#5BAE44", "Hadir"), ("#F0C84B", "Izin"), ("#D94A38", "Alpa")]:
            row = QHBoxLayout()
            dot = QLabel()
            dot.setFixedSize(16, 16)
            dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
            label = QLabel(text)
            label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 13px; font-weight: 700;")
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
        task.setStyleSheet(f"color: {TEXT_DARK}; font-size: 13px; font-weight: 700;")

        badge = QLabel(badge_text)
        badge.setStyleSheet(
            f"background: {badge_color}; color: {TEXT_DARK}; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 700;"
        )

        layout.addWidget(task)
        layout.addStretch(1)
        layout.addWidget(badge)
        return row

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setFixedHeight(42)
        footer.setStyleSheet("background: #F4F7FB; border-top: 1px solid #DCE4EE;")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(14, 0, 14, 0)
        label = QLabel("© 2026 Sistem Kebun  |  Versi 1.0")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 13px; font-weight: 700;")
        layout.addWidget(label)
        return footer


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
