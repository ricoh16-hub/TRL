from datetime import date
from typing import Optional

from PySide6.QtCore import Property, QEvent, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtGui import QColor, QEnterEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from database.models import User
except ImportError:
    from src.database.models import User  # type: ignore[no-redef]

_active_dashboard: Optional["DashboardForm"] = None

NAVY_TOP = "#163A69"
NAVY_SIDE = "#1C467A"
NAVY_SELECTED = "#244F89"
PAGE_BG = "#EFF3F8"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#22324A"
TEXT_SOFT = "#70829A"


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
    def __init__(self, text: str, active: bool = False) -> None:
        super().__init__(text)
        self._active = active
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
        super().mouseReleaseEvent(event)


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


class DashboardForm(QMainWindow):
    def __init__(self, user: Optional[User] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user
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
        content_row.addWidget(self._build_content(), 1)

        body = QWidget()
        body.setLayout(content_row)
        root_layout.addWidget(body, 1)
        root_layout.addWidget(self._build_footer())

        self.setCentralWidget(root)

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
            ("Dashboard", True),
            ("Data Master", False),
            ("Data Karyawan", False),
            ("Data Divisi", False),
            ("Data Blok", False),
            ("Transaksi", False),
            ("Input Kegiatan", False),
            ("Absensi", False),
            ("Panen", False),
            ("Laporan", False),
            ("Inventaris", False),
            ("Pengaturan", False),
            ("Manajemen User", False),
        ]

        for item_text, active in menu_items:
            item = AnimatedNavItem(item_text, active=active)
            layout.addWidget(item)

        layout.addStretch(1)
        return sidebar

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
