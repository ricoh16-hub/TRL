from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedSize(108, 40)
        logout_btn.setStyleSheet(
            "QPushButton { background: #D94A38; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; }"
            "QPushButton:hover { background: #BF3C2C; }"
        )
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
            item = QLabel(item_text)
            item.setFixedHeight(38)
            item.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            item.setContentsMargins(22, 0, 0, 0)
            bg = NAVY_SELECTED if active else NAVY_SIDE
            weight = 800 if active else 600
            item.setStyleSheet(
                f"background: {bg}; color: white; font-size: 14px; font-weight: {weight};"
                "border-left: 4px solid #FFFFFF; padding-left: 18px;"
                if active
                else "background: transparent; color: white; font-size: 14px; font-weight: 600; padding-left: 22px;"
            )
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
        top_cards.addWidget(InfoCard("🏭", "Total Produksi", "52,300 Kg", "#1D4ED8"), 0, 0)
        top_cards.addWidget(InfoCard("✅", "Kehadiran Hari Ini", "85 Hadir", "#5BAE44"), 0, 1)
        top_cards.addWidget(InfoCard("⚙", "Status Pekerjaan", "5 Tugas Berjalan", "#5BAE44"), 0, 2)
        top_cards.addWidget(InfoCard("🔔", "Notifikasi", "2 Pesan Baru", "#D94A38"), 0, 3)
        layout.addLayout(top_cards)

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(16)
        main_grid.setVerticalSpacing(16)

        production = SectionCard("Grafik Produksi")
        production.body_layout.addWidget(self._make_chart_placeholder())
        production.body_layout.addStretch(1)

        attendance = SectionCard("Absensi Karyawan")
        attendance.body_layout.addWidget(self._make_attendance_placeholder())

        tasks = SectionCard("Pekerjaan Hari Ini")
        for task_text, badge_text, badge_color in [
            ("Perawatan Blok A1", "Sedang Berlangsung", "#D7E8F8"),
            ("Panen Blok C3", "Dalam Proses", "#F7D7D6"),
            ("Penyemprotan Blok B2", "Belum Selesai", "#F6EEBD"),
        ]:
            tasks.body_layout.addWidget(self._make_task_row(task_text, badge_text, badge_color))

        notifications = SectionCard("Notifikasi")
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
