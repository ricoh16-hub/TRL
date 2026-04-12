from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QToolButton, QVBoxLayout, QWidget

try:
    from ui.flow_auth import authenticate_credentials_step
except ImportError:
    from src.ui.flow_auth import authenticate_credentials_step

try:
    from database.models import User
except ImportError:
    from src.database.models import User


def _draw_lock_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    stroke = max(1.4, size * 0.08)
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    body_w = size * 0.48
    body_h = size * 0.34
    body_x = (size - body_w) / 2
    body_y = size * 0.5
    painter.drawRoundedRect(body_x, body_y, body_w, body_h, size * 0.08, size * 0.08)

    arc = QPainterPath()
    arc.moveTo(size * 0.34, size * 0.52)
    arc.cubicTo(size * 0.34, size * 0.28, size * 0.66, size * 0.28, size * 0.66, size * 0.52)
    painter.drawPath(arc)

    painter.end()
    return pixmap


def _draw_user_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
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
    painter.drawEllipse(head_x, head_y, head_size, head_size)

    shoulder = QPainterPath()
    shoulder.moveTo(size * 0.18, size * 0.78)
    shoulder.cubicTo(size * 0.22, size * 0.58, size * 0.78, size * 0.58, size * 0.82, size * 0.78)
    painter.drawPath(shoulder)

    painter.end()
    return pixmap


def _draw_eye_icon(size: int, color: QColor, crossed: bool = False) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    stroke = max(1.2, size * 0.08)
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    outer = QPainterPath()
    outer.moveTo(size * 0.14, size * 0.5)
    outer.cubicTo(size * 0.27, size * 0.28, size * 0.73, size * 0.28, size * 0.86, size * 0.5)
    outer.cubicTo(size * 0.73, size * 0.72, size * 0.27, size * 0.72, size * 0.14, size * 0.5)
    painter.drawPath(outer)

    iris_size = size * 0.24
    iris_x = (size - iris_size) / 2
    iris_y = (size - iris_size) / 2
    painter.drawEllipse(iris_x, iris_y, iris_size, iris_size)

    if crossed:
        slash = QPen(color, stroke)
        slash.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(slash)
        painter.drawLine(int(size * 0.2), int(size * 0.82), int(size * 0.82), int(size * 0.2))

    painter.end()
    return pixmap


def _draw_check_icon(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    stroke = max(1.2, size * 0.09)
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawRoundedRect(size * 0.14, size * 0.14, size * 0.72, size * 0.72, size * 0.16, size * 0.16)
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

    dialog.setStyleSheet(
        """
        QDialog#credentialsDialog {
            background: qlineargradient(
                x1:0,
                y1:0,
                x2:1,
                y2:1,
                stop:0 #222a36,
                stop:1 #3a4a5c
            );
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.18);
        }

        QLabel {
            color: #f4f8ff;
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
            font-size: 15px;
        }

        QFrame#badgeOuter {
            border-radius: 42px;
            border: 1px solid rgba(88, 138, 255, 0.45);
            background: rgba(5, 20, 65, 0.35);
        }

        QFrame#badgeInner {
            border-radius: 31px;
            border: 1px solid rgba(90, 156, 255, 0.5);
            background: qradialgradient(
                cx:0.5,
                cy:0.42,
                radius:0.9,
                stop:0 rgba(102, 162, 255, 0.45),
                stop:1 rgba(14, 35, 85, 0.8)
            );
        }

        QLabel#badgeText {
            font-size: 14px;
            font-weight: 700;
            color: #dbe8ff;
        }

        QLabel#title {
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 0.2px;
            color: #ecf2ff;
        }

        QLabel#subtitle {
            font-size: 12px;
            color: rgba(233, 241, 255, 0.70);
        }

        QFrame#cardPanel {
            border: 1px solid rgba(127, 174, 255, 0.45);
            border-radius: 28px;
            background: qlineargradient(
                x1:0,
                y1:0,
                x2:1,
                y2:1,
                stop:0 rgba(10, 23, 73, 0.88),
                stop:1 rgba(24, 44, 111, 0.88)
            );
        }

        QFrame#leftGlow,
        QFrame#rightGlow {
            border: none;
            background: qlineargradient(
                x1:0,
                y1:0,
                x2:0,
                y2:1,
                stop:0 rgba(127, 187, 255, 0),
                stop:0.5 rgba(127, 187, 255, 0.65),
                stop:1 rgba(127, 187, 255, 0)
            );
        }

        QFrame#topGlow {
            border: none;
            background: qlineargradient(
                x1:0,
                y1:0,
                x2:1,
                y2:0,
                stop:0 rgba(170, 205, 255, 0),
                stop:0.5 rgba(202, 227, 255, 0.95),
                stop:1 rgba(170, 205, 255, 0)
            );
        }

        QLabel#fieldLabel {
            font-size: 13px;
            font-weight: 600;
            color: #e9f1ff;
        }

        QFrame#inputRow {
            border: 1px solid rgba(130, 170, 255, 0.34);
            border-radius: 16px;
            background: rgba(18, 33, 83, 0.72);
        }

        QLabel#fieldIcon {
            min-width: 26px;
        }

        QLineEdit#fieldInput {
            color: #edf4ff;
            border: none;
            background: transparent;
            padding: 10px 6px;
            font-size: 12px;
            font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;
        }

        QLineEdit#fieldInput::placeholder {
            color: rgba(214, 228, 255, 0.48);
        }

        QToolButton#togglePassword {
            border: none;
            background: transparent;
            padding: 2px 4px;
        }

        QLabel#statusIcon {
            min-width: 20px;
        }

        QLabel#statusText {
            color: rgba(220, 232, 255, 0.9);
            font-size: 12px;
        }

        QPushButton {
            border-radius: 15px;
            padding: 9px 14px;
            font-size: 12px;
            font-weight: 700;
            min-height: 24px;
        }

        QPushButton#cancelButton {
            border: 1px solid rgba(126, 170, 255, 0.38);
            color: #eaf1ff;
            background: rgba(12, 24, 70, 0.65);
        }

        QPushButton#cancelButton:hover {
            background: rgba(24, 42, 99, 0.9);
        }

        QPushButton#submitButton {
            color: white;
            border: 1px solid rgba(145, 191, 255, 0.42);
            background: qlineargradient(
                x1:0,
                y1:0,
                x2:1,
                y2:0,
                stop:0 #3f6fff,
                stop:1 #5ea0ff
            );
        }

        QPushButton#submitButton:hover {
            background: qlineargradient(
                x1:0,
                y1:0,
                x2:1,
                y2:0,
                stop:0 #4b79ff,
                stop:1 #6badff
            );
        }
        """
    )

    root_layout = QVBoxLayout(dialog)
    root_layout.setContentsMargins(42, 28, 42, 24)
    root_layout.setSpacing(12)

    title = QLabel(
        "<p style='margin:0; padding:0;'>Secure <span style='color:#5f8fff;'>Access</span> Point</p>"
        "<p style='margin:1px 0 0 0; padding:0; font-size:12px; color:rgba(233,241,255,0.70); font-weight:400;'>"
        "Enter your credentials to continue securely"
        "</p>"
    )
    title.setObjectName("title")
    title.setTextFormat(Qt.TextFormat.RichText)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root_layout.addWidget(title)

    card = QFrame()
    card.setObjectName("cardPanel")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(24, 14, 24, 20)
    card_layout.setSpacing(10)

    side_glow_row = QHBoxLayout()
    side_glow_row.setContentsMargins(0, 0, 0, 0)
    side_glow_row.setSpacing(0)
    left_glow = QFrame()
    left_glow.setObjectName("leftGlow")
    left_glow.setFixedWidth(1)
    right_glow = QFrame()
    right_glow.setObjectName("rightGlow")
    right_glow.setFixedWidth(1)
    side_glow_row.addWidget(left_glow)
    side_glow_row.addStretch(1)
    side_glow_row.addWidget(right_glow)
    card_layout.addLayout(side_glow_row)

    top_glow = QFrame()
    top_glow.setObjectName("topGlow")
    top_glow.setFixedHeight(3)
    card_layout.addWidget(top_glow)

    username_label = QLabel("Username")
    username_label.setObjectName("fieldLabel")
    card_layout.addWidget(username_label)

    username_row = QFrame()
    username_row.setObjectName("inputRow")
    username_layout = QHBoxLayout(username_row)
    username_layout.setContentsMargins(12, 0, 12, 0)
    username_layout.setSpacing(8)

    username_icon = QLabel()
    username_icon.setObjectName("fieldIcon")
    _set_icon(username_icon, _draw_user_icon(16, QColor("#c9defc")))

    username_input = QLineEdit()
    username_input.setObjectName("fieldInput")
    username_input.setPlaceholderText("Enter your username")

    username_layout.addWidget(username_icon)
    username_layout.addWidget(username_input)
    card_layout.addWidget(username_row)

    password_label = QLabel("Password")
    password_label.setObjectName("fieldLabel")
    card_layout.addWidget(password_label)

    password_row = QFrame()
    password_row.setObjectName("inputRow")
    password_layout = QHBoxLayout(password_row)
    password_layout.setContentsMargins(12, 0, 12, 0)
    password_layout.setSpacing(8)

    password_icon = QLabel()
    password_icon.setObjectName("fieldIcon")
    _set_icon(password_icon, _draw_lock_icon(16, QColor("#c9defc")))

    password_input = QLineEdit()
    password_input.setObjectName("fieldInput")
    password_input.setEchoMode(QLineEdit.EchoMode.Password)
    password_input.setPlaceholderText("Enter your password")

    toggle_password_btn = QToolButton()
    toggle_password_btn.setObjectName("togglePassword")
    toggle_password_btn.setIconSize(password_icon.pixmap().size() if password_icon.pixmap() is not None else QSize(14, 14))
    toggle_password_btn.setIcon(QIcon(_draw_eye_icon(14, QColor("#d3e6ff"), crossed=False)))
    toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    password_layout.addWidget(password_icon)
    password_layout.addWidget(password_input)
    password_layout.addWidget(toggle_password_btn)
    card_layout.addWidget(password_row)

    status_row = QHBoxLayout()
    status_row.setSpacing(7)
    status_icon = QLabel()
    status_icon.setObjectName("statusIcon")
    _set_icon(status_icon, _draw_check_icon(14, QColor("#7fc3ff")))
    status_text = QLabel(f"PIN verified for user: <b>{getattr(pin_user, 'username', '-')}</b>")
    status_text.setObjectName("statusText")
    status_text.setTextFormat(Qt.TextFormat.RichText)
    status_row.addWidget(status_icon)
    status_row.addWidget(status_text)
    status_row.addStretch(1)
    card_layout.addLayout(status_row)

    root_layout.addWidget(card)

    result_user: dict[str, Optional[User]] = {"user": None}

    buttons = QHBoxLayout()
    buttons.setSpacing(12)
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setObjectName("cancelButton")
    submit_btn = QPushButton("Sign In   ->")
    submit_btn.setObjectName("submitButton")
    buttons.addWidget(cancel_btn)
    buttons.addWidget(submit_btn)
    root_layout.addLayout(buttons)

    def toggle_password_visibility() -> None:
        is_hidden = password_input.echoMode() == QLineEdit.EchoMode.Password
        password_input.setEchoMode(QLineEdit.EchoMode.Normal if is_hidden else QLineEdit.EchoMode.Password)
        toggle_password_btn.setIcon(QIcon(_draw_eye_icon(14, QColor("#d3e6ff"), crossed=is_hidden)))

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

    toggle_password_btn.clicked.connect(toggle_password_visibility)
    submit_btn.clicked.connect(on_submit)
    cancel_btn.clicked.connect(dialog.reject)

    username_input.setFocus()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result_user["user"]
    return None
