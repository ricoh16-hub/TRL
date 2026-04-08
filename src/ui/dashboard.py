from datetime import date
from typing import Optional, TypedDict

from PySide6.QtCore import Property, QEvent, QPropertyAnimation, QEasingCurve, Qt, Signal
from PySide6.QtGui import QColor, QEnterEvent, QMouseEvent
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
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from database.models import Session, User
except ImportError:
    from src.database.models import Session, User  # type: ignore[no-redef]

try:
    from database.crud import delete_user, update_user
except ImportError:
    from src.database.crud import delete_user, update_user  # type: ignore[no-redef]

_active_dashboard: Optional["DashboardForm"] = None

NAVY_TOP = "#163A69"
NAVY_SIDE = "#1C467A"
NAVY_SELECTED = "#244F89"
PAGE_BG = "#EFF3F8"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#22324A"
TEXT_SOFT = "#70829A"


class UserRow(TypedDict):
    id: int
    username: str
    nama: str
    role: str
    status: str


def _apply_card_shadow(widget: QWidget) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(15, 30, 55, 45))
    widget.setGraphicsEffect(shadow)


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


class UserEditDialog(QDialog):
    def __init__(
        self,
        username: str,
        nama: str,
        role: str,
        status: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit User")
        self.setModal(True)
        self.resize(420, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._username_input = QLineEdit(username)
        self._nama_input = QLineEdit(nama)

        self._role_combo = QComboBox()
        self._role_combo.addItems(["user", "admin"])
        self._role_combo.setCurrentText(role.lower() if role.lower() in {"user", "admin"} else "user")

        self._status_combo = QComboBox()
        self._status_combo.addItems(["Aktif", "Nonaktif"])
        self._status_combo.setCurrentText("Aktif" if status.lower() == "aktif" else "Nonaktif")

        form.addRow("Username", self._username_input)
        form.addRow("Nama", self._nama_input)
        form.addRow("Role", self._role_combo)
        form.addRow("Status", self._status_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def data(self) -> dict[str, str]:
        return {
            "username": self._username_input.text().strip(),
            "nama": self._nama_input.text().strip(),
            "role": self._role_combo.currentText().strip().lower(),
            "status": self._status_combo.currentText().strip().lower(),
        }


class UserAddDialog(QDialog):
    """Dialog untuk menambahkan user baru"""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tambah User")
        self.setModal(True)
        self.resize(420, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Contoh: riko01")
        
        self._nama_input = QLineEdit()
        self._nama_input.setPlaceholderText("Contoh: Riko Sinaga")
        
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Password untuk login")
        
        self._role_combo = QComboBox()
        self._role_combo.addItems(["Admin", "Manager", "Staff"])
        
        self._status_combo = QComboBox()
        self._status_combo.addItems(["Aktif", "Nonaktif"])

        form.addRow("Username", self._username_input)
        form.addRow("Nama", self._nama_input)
        form.addRow("Password", self._password_input)
        form.addRow("Role", self._role_combo)
        form.addRow("Status", self._status_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Simpan")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Batal")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def data(self) -> dict[str, str]:
        return {
            "username": self._username_input.text().strip(),
            "nama": self._nama_input.text().strip(),
            "password": self._password_input.text(),
            "role": self._role_combo.currentText().strip().lower(),
            "status": self._status_combo.currentText().strip().lower(),
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
        role = getattr(self._user, "role", "user") if self._user is not None else "user"
        date_text = date.today().strftime("%d %B %Y")
        user_info = QLabel(f"User: {username}  |  Level: {str(role).title()}\nTanggal: {date_text}")
        user_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        user_info.setStyleSheet("color: white; font-size: 12px; font-weight: 600;")

        logout_btn = AnimatedActionButton("Logout")
        logout_btn.setFixedSize(108, 40)
        logout_btn.clicked.connect(self.close)

        layout.addWidget(brand)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(user_info)
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
            ("manajemen_user", "Manajemen User"),
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

        title = QLabel("Manajemen User")
        title.setStyleSheet(f"color: {TEXT_DARK}; font-size: 38px; font-weight: 800;")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._search_username = QLineEdit()
        self._search_username.setPlaceholderText("Cari Username...")
        self._search_username.setFixedHeight(36)
        self._search_username.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid #D7E0EA; border-radius: 8px; padding: 0 12px; font-size: 14px; }"
        )
        self._search_username.textChanged.connect(self._apply_user_filters)

        filter_label = QLabel("Filter Role")
        filter_label.setStyleSheet(f"color: {TEXT_SOFT}; font-size: 14px; font-weight: 700;")

        self._role_filter = QComboBox()
        self._role_filter.addItem("All")
        self._role_filter.setFixedHeight(36)
        self._role_filter.setMinimumWidth(180)
        self._role_filter.setStyleSheet(
            "QComboBox { background: white; border: 1px solid #D7E0EA; border-radius: 8px; padding: 0 10px; font-size: 14px; }"
        )
        self._role_filter.currentTextChanged.connect(self._apply_user_filters)

        add_user_btn = QPushButton("+ Tambah User")
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
        self._users_table.setColumnCount(6)
        self._users_table.setHorizontalHeaderLabels(["No", "Username", "Nama", "Role", "Status", "Aksi"])
        self._users_table.verticalHeader().setVisible(False)
        self._users_table.setAlternatingRowColors(True)
        self._users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._users_table.setStyleSheet(
            "QTableWidget { background: white; border: 1px solid #DCE5EF; border-radius: 10px; gridline-color: #E7EDF4; font-size: 14px; }"
            "QHeaderView::section { background: #F2F6FB; color: #2D405C; font-size: 14px; font-weight: 700; border: none; border-right: 1px solid #E7EDF4; padding: 10px; }"
            "QTableWidget::item { padding: 8px; color: #2D405C; }"
            "QTableWidget::item:selected { background: #E7F1FF; color: #1F3F66; }"
        )

        header = self._users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._users_table, 1)
        return page

    def _load_users_table(self) -> None:
        if self._users_table is None or self._role_filter is None:
            return

        session = Session()
        try:
            # CRITICAL: Pre-load role_links before closing session to prevent DetachedInstanceError
            # when accessing user.role property later
            from sqlalchemy.orm import selectinload
            users = session.query(User).options(selectinload(User.role_links)).order_by(User.id.asc()).all()
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
            nama = str(getattr(user, "nama", "") or "").strip()
            role = str(getattr(user, "role", "user") or "user").strip()
            status = str(getattr(user, "status", "aktif") or "aktif").strip().lower()
            row: UserRow = {
                "id": user_id,
                "username": username,
                "nama": nama or username.replace("_", " ").title(),
                "role": role.capitalize(),
                "status": "Aktif" if status == "aktif" else "Nonaktif",
            }
            self._all_users_rows.append(row)
            role_values.add(role.capitalize())

        self._role_filter.blockSignals(True)
        self._role_filter.clear()
        self._role_filter.addItem("All")
        for value in sorted(role_values):
            self._role_filter.addItem(value)
        self._role_filter.blockSignals(False)

        self._apply_user_filters()

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

        self._users_table.setRowCount(len(filtered_rows))
        for row_index, row in enumerate(filtered_rows, start=1):
            self._users_table.setItem(row_index - 1, 0, QTableWidgetItem(str(row_index)))
            self._users_table.setItem(row_index - 1, 1, QTableWidgetItem(str(row["username"])))
            self._users_table.setItem(row_index - 1, 2, QTableWidgetItem(str(row["nama"])))
            self._users_table.setItem(row_index - 1, 3, QTableWidgetItem(str(row["role"])))
            status_value = str(row["status"])
            status_item = QTableWidgetItem(status_value)
            if status_value.lower() == "aktif":
                status_item.setForeground(QColor("#2E7D32"))
            else:
                status_item.setForeground(QColor("#A63D40"))
            self._users_table.setItem(row_index - 1, 4, status_item)

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(
                "QPushButton { background: #E8F1FF; color: #2559A6; border: 1px solid #C8DBF8; border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 700; }"
            )
            row_id = row["id"]
            edit_btn.clicked.connect(
                lambda _checked=False, user_id=row_id: self._edit_user(user_id)
            )

            delete_btn = QPushButton("Hapus")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet(
                "QPushButton { background: #FEEBEC; color: #B5353A; border: 1px solid #F6C7CA; border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 700; }"
            )
            row_username = row["username"]
            delete_btn.clicked.connect(
                lambda _checked=False, user_id=row_id, username=row_username: self._delete_user(user_id, username)
            )

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self._users_table.setCellWidget(row_index - 1, 5, actions)

    def _edit_user(self, user_id: int) -> None:
        session = Session()
        try:
            user = session.get(User, user_id)
            if user is None:
                QMessageBox.warning(self, "Data Tidak Ditemukan", "User tidak ditemukan.")
                return

            dialog = UserEditDialog(
                username=str(getattr(user, "username", "") or ""),
                nama=str(getattr(user, "nama", "") or ""),
                role=str(getattr(user, "role", "user") or "user"),
                status=str(getattr(user, "status", "aktif") or "aktif"),
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            payload = dialog.data()
            if not payload["username"]:
                QMessageBox.warning(self, "Validasi", "Username tidak boleh kosong.")
                return

            update_user(
                session,
                user_id,
                username=payload["username"],
                nama=payload["nama"],
                role=payload["role"],
                status=payload["status"],
            )
        except ValueError as error:
            QMessageBox.warning(self, "Validasi", str(error))
            return
        finally:
            session.close()

        self._load_users_table()

    def _delete_user(self, user_id: int, username: str) -> None:
        answer = QMessageBox.question(
            self,
            "Hapus User",
            f"Hapus user '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        session = Session()
        try:
            delete_user(session, user_id)
        except ValueError as error:
            QMessageBox.warning(self, "Gagal Hapus", str(error))
            return
        finally:
            session.close()

        self._load_users_table()

    def _open_add_user_dialog(self) -> None:
        """Buka dialog untuk menambah user baru"""
        dialog = UserAddDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        data = dialog.data()
        
        # Validasi
        if not data["username"]:
            QMessageBox.warning(self, "Validasi", "Username tidak boleh kosong.")
            return
        
        if not data["nama"]:
            QMessageBox.warning(self, "Validasi", "Nama tidak boleh kosong.")
            return
        
        if not data["password"]:
            QMessageBox.warning(self, "Validasi", "Password tidak boleh kosong.")
            return
        
        self._add_user(data)

    def _add_user(self, data: dict[str, str]) -> None:
        """Tambahkan user baru ke database"""
        session = Session()
        try:
            from database.crud import create_user
            
            create_user(
                session,
                username=data["username"],
                nama=data["nama"],
                password=data["password"],
                role=data["role"],
                status=data["status"],
            )
            self._load_users_table()
            QMessageBox.information(
                self,
                "Berhasil",
                f"User '{data['username']}' berhasil ditambahkan."
            )
        except ValueError as error:
            QMessageBox.warning(self, "Validasi", str(error))
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
        _active_dashboard.raise_()
        _active_dashboard.activateWindow()
        return _active_dashboard

    _active_dashboard = DashboardForm(user=user)
    _active_dashboard.showMaximized()
    _active_dashboard.raise_()
    _active_dashboard.activateWindow()
    return _active_dashboard
