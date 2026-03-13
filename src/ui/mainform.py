from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QListWidget, QLabel, QGraphicsDropShadowEffect, QGraphicsBlurEffect, QApplication
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtGui import QColor
import sys
import os
from typing import cast
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.userform import UserForm
from ui.webform import WebForm

class MainForm(QMainWindow):
    """
    Main window aplikasi utama, menampilkan sidebar dan halaman User/Web/Settings.
    Menggunakan QStackedWidget untuk navigasi antar halaman.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Database SQL Python App')
        self.setMinimumSize(900, 600)
        # Apply SF font to all widgets in mainform
        sf_style = """
        * {
            font-family: 'SF Pro Display', 'San Francisco', 'Arial', sans-serif;
        }
        """
        self.setStyleSheet(sf_style)

        # Futuristic icon for mainform
        icon_label = QLabel("🚀")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setColor(QColor("cyan"))
        shadow.setOffset(0, 8)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(12)
        icon_label.setGraphicsEffect(shadow)
        icon_label.setGraphicsEffect(blur)

        self.sidebar = QListWidget()
        self.sidebar.addItems(['Dashboard', 'User', 'Web', 'Settings'])
        # Dynamic shading for sidebar
        sidebar_shadow = QGraphicsDropShadowEffect()
        sidebar_shadow.setBlurRadius(24)
        sidebar_shadow.setColor(QColor("cyan"))
        sidebar_shadow.setOffset(0, 4)
        sidebar_blur = QGraphicsBlurEffect()
        sidebar_blur.setBlurRadius(8)
        self.sidebar.setGraphicsEffect(sidebar_shadow)
        self.sidebar.setGraphicsEffect(sidebar_blur)

        self.pages = QStackedWidget()
        self.pages.addWidget(QWidget())  # Dashboard
        self.pages.addWidget(UserForm())  # User CRUD
        self.pages.addWidget(WebForm())  # Hybrid Web
        self.pages.addWidget(QWidget())  # Settings

        layout = QVBoxLayout()
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages)
        layout.addStretch(1)  # Tambahkan stretch agar responsif
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.sidebar.currentRowChanged.connect(self.animate_page_change)

    def animate_page_change(self, index: int) -> None:
        if index < 0 or index >= self.pages.count():
            return

        current_widget = self.pages.currentWidget()
        next_widget = cast(QWidget, self.pages.widget(index))

        if current_widget is not next_widget:
            fade_out = QPropertyAnimation(current_widget, b"windowOpacity")
            fade_out.setDuration(220)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
            fade_in = QPropertyAnimation(next_widget, b"windowOpacity")
            fade_in.setDuration(220)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
            def switch():
                self.pages.setCurrentIndex(index)
                fade_in.start()
            fade_out.finished.connect(switch)
            fade_out.start()

    def get_shackle_angle(self):
        return getattr(self, '_shackle_angle', 180)

def show_main_form(app: QApplication):
    window = MainForm()
    window.show()
    app.exec()