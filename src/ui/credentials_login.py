from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

try:
    from ui.flow_auth import authenticate_credentials_step
except ImportError:
    from src.ui.flow_auth import authenticate_credentials_step

try:
    from database.models import User
except ImportError:
    from src.database.models import User


def show_credentials_login(app: QApplication, pin_user: User, parent: Optional[QWidget] = None) -> Optional[User]:
    """Step 2: username/password validation after successful PIN step."""
    dialog = QDialog(parent)
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

    dialog.setStyleSheet(
        """
        QDialog {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #222a36, stop:1 #3a4a5c);
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.18);
        }
        QLabel {
            color: white;
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
            font-size: 14px;
        }
        QLineEdit {
            color: white;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 10px;
            padding: 8px 10px;
            font-size: 14px;
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
        }
        QPushButton {
            background: #4f8ff8;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 8px 14px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #3c7be0;
        }
        """
    )

    root_layout = QVBoxLayout(dialog)
    root_layout.setContentsMargins(26, 22, 26, 22)
    root_layout.setSpacing(12)

    title = QLabel("Step 2: Username & Password")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root_layout.addWidget(title)

    helper = QLabel(f"PIN valid untuk user: {getattr(pin_user, 'username', '-')}")
    helper.setAlignment(Qt.AlignmentFlag.AlignCenter)
    helper.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 12px;")
    root_layout.addWidget(helper)

    form = QFormLayout()
    form.setSpacing(10)
    username_input = QLineEdit()
    username_input.setPlaceholderText("Username")
    password_input = QLineEdit()
    password_input.setEchoMode(QLineEdit.EchoMode.Password)
    password_input.setPlaceholderText("Password")
    form.addRow("Username", username_input)
    form.addRow("Password", password_input)
    root_layout.addLayout(form)

    result_user: dict[str, Optional[User]] = {"user": None}

    buttons = QHBoxLayout()
    cancel_btn = QPushButton("Batal")
    submit_btn = QPushButton("Lanjut")
    buttons.addWidget(cancel_btn)
    buttons.addWidget(submit_btn)
    root_layout.addLayout(buttons)

    def on_submit() -> None:
        username = username_input.text().strip()
        password = password_input.text()
        if not username or not password:
            QMessageBox.warning(dialog, "Validasi", "Username dan password wajib diisi.")
            return

        authenticated_user = authenticate_credentials_step(
            pin_user=pin_user,
            username=username,
            password=password,
            ip_address="local-app",
            user_agent="PySide6",
        )
        if authenticated_user is None:
            QMessageBox.warning(dialog, "Login Ditolak", "Username/password tidak valid atau akun terkunci.")
            return

        result_user["user"] = authenticated_user
        dialog.accept()

    submit_btn.clicked.connect(on_submit)
    cancel_btn.clicked.connect(dialog.reject)

    username_input.setFocus()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result_user["user"]
    return None
