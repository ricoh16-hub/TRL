from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QToolButton, QVBoxLayout, QWidget
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from ui.custom_button import CustomButton
from PySide6.QtGui import QColor

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

    stroke = 0.5
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


    # Putar seluruh ikon 45 derajat CCW (kiri)
    # Gembok modern diperbesar: body dan arc lebih dominan
    body_w = size * 0.68
    body_h = size * 0.48
    body_x = (size - body_w) / 2
    body_y = size * 0.54 - body_h * 0.18
    painter.drawRoundedRect(body_x, body_y, body_w, body_h, size * 0.13, size * 0.13)

    # Arc setengah lingkaran di atas body (lebih besar)
    arc_radius = body_w * 0.52
    arc_center_x = size / 2
    arc_center_y = body_y
    arc_rect_x = arc_center_x - arc_radius
    arc_rect_y = arc_center_y - arc_radius
    arc_rect_w = arc_radius * 2
    arc_rect_h = arc_radius * 2

    arc = QPainterPath()
    arc.moveTo(arc_rect_x, arc_center_y)
    arc.arcTo(arc_rect_x, arc_rect_y, arc_rect_w, arc_rect_h, 180, -180)
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

    stroke = 1
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
        card_border="rgba(180, 180, 180, 0.35)",
        card_bg0="rgba(30, 30, 30, 0.90)", card_bg1="rgba(60, 60, 60, 0.90)",
        glow="rgba(255,255,255,0.28)",
        label_color="#FFFFFF",
        input_border="rgba(180, 180, 180, 0.35)",
        input_row_bg="rgba(40, 40, 60, 0.68)",
        status_color="#FFFFFF",
        cancel_border="#FFFFFF",
        cancel_color="#FFFFFF",
        submit_border="#FFFFFF",
        submit0="#222a36", submit1="#3a4a5c",
        submit_h0="#3a4a5c", submit_h1="#edf4ff",
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
        "<p style='margin:0; padding:0; font-size:22px; font-weight:700; letter-spacing:0.5px; color:#ecf2ff;'>"
        "Secure <span style='color:#5f8fff;'>Access</span> Point</p>"
        "<p style='margin:4px 0 0 0; padding:0; font-size:12px; color:rgba(233,241,255,0.65); font-weight:400;'>"
        "Enter your credentials to continue securely</p>"
    )
    _TITLE_CHARGING = (
        "<p style='margin:0; padding:0; font-size:22px; font-weight:700; letter-spacing:0.5px; color:#50B4FF;'>"
        "Secure <span style='color:#7dd8ff;'>Access</span> Point</p>"
        "<p style='margin:4px 0 0 0; padding:0; font-size:12px; color:rgba(80,200,255,0.75); font-weight:400;'>"
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
    root_layout.addWidget(title)
    root_layout.addSpacing(20)

    card = QFrame()
    card.setObjectName("cardPanel")
    # Shadow utama (putih)
    card_shadow = QGraphicsDropShadowEffect(card)
    card_shadow.setBlurRadius(16)
    card_shadow.setOffset(3, 4)
    card_shadow.setColor(QColor(255, 255, 255, 60))
    card.setGraphicsEffect(card_shadow)

    # Shadow kedua (biru muda transparan, harmonis dengan background)
    card_shadow2 = QGraphicsDropShadowEffect(card)
    card_shadow2.setBlurRadius(32)
    card_shadow2.setOffset(0, 0)
    card_shadow2.setColor(QColor(180, 180, 180, 40))
    # Agar kedua efek tampil, letakkan shadow kedua di parent panel
    card.setGraphicsEffect(card_shadow)
    card.parentWidget().setGraphicsEffect(card_shadow2) if card.parentWidget() else None
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(24, 18, 24, 22)
    card_layout.setSpacing(10)

    from PySide6.QtCore import QPropertyAnimation, Property
    from PySide6.QtGui import QPainter, QLinearGradient, QBrush


    class ShimmerGlow(QFrame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("topGlow")
            self.setFixedHeight(2)
            self._charging = False
            self._color_charging = QColor(80, 180, 255, 180)
            self._color_charging_core = QColor(80, 180, 255, 255)
            self._color_normal = QColor(202, 227, 255, 160)
            self._color_normal_core = QColor(202, 227, 255, 255)
            self._shimmer_active = True
            self._shimmer_pos = 0.0
            from PySide6.QtCore import QEasingCurve, QSequentialAnimationGroup, QPauseAnimation, QPropertyAnimation

            self._anim_group = QSequentialAnimationGroup(self)
            shimmer_anim = QPropertyAnimation(self, b"shimmerPos")
            shimmer_anim.setStartValue(0.0)
            shimmer_anim.setEndValue(1.0)
            shimmer_anim.setDuration(2000)  # 2 detik per siklus
            shimmer_anim.setEasingCurve(QEasingCurve.Linear)
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

        def getShimmerPos(self):
            return self._shimmer_pos

        def setShimmerPos(self, value):
            self._shimmer_pos = value
            self.update()

        from PySide6.QtCore import Property
        shimmerPos = Property(float, getShimmerPos, setShimmerPos)

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
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
            painter.setPen(Qt.NoPen)
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
    if hasattr(top_glow, 'start_shimmer'):
        top_glow.start_shimmer()

    username_label = QLabel("User")
    username_label.setObjectName("fieldLabel")
    # Efek glow awal
    username_glow = QGraphicsDropShadowEffect(username_label)
    username_glow.setBlurRadius(7)
    username_glow.setOffset(0, 0)
    username_glow.setColor(QColor(255, 255, 255, 70))
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
    _set_icon(username_icon, _draw_user_icon(18, QColor("#c9defc")))

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
    password_glow.setColor(QColor(255, 255, 255, 70))
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
    _set_icon(password_icon, _draw_lock_icon(18, QColor("#c9defc")))

    password_input = QLineEdit()
    password_input.setObjectName("fieldInput")
    password_input.setEchoMode(QLineEdit.EchoMode.Password)
    password_input.setPlaceholderText("Enter your password")

    toggle_password_btn = QToolButton()
    toggle_password_btn.setObjectName("togglePassword")
    toggle_password_btn.setIconSize(QSize(16, 16))
    toggle_password_btn.setIcon(QIcon(_draw_eye_icon(16, QColor("#d3e6ff"), crossed=False)))
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
    _set_icon(status_icon, _draw_check_icon(16, QColor("#7fc3ff")))
    status_text = QLabel(f"PIN verified for user: <span style='font-size:15px;'><b>{getattr(pin_user, 'username', '-')}</b></span>")
    status_text.setObjectName("statusText")
    status_text.setTextFormat(Qt.TextFormat.RichText)
    # Efek glow awal
    status_glow = QGraphicsDropShadowEffect(status_text)
    status_glow.setBlurRadius(7)
    status_glow.setOffset(0, 0)
    status_glow.setColor(QColor(255, 255, 255, 70))
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
    cancel_btn.setStyleSheet("")  # Kosongkan stylesheet agar tidak override
    submit_btn = CustomButton("Sign In", primary=True)
    submit_btn.setObjectName("submitButtonFixed")
    submit_btn.setMinimumSize(100, 41)
    submit_btn.setMaximumSize(100, 41)
    submit_btn.setStyleSheet("")
    for btn in [cancel_btn, submit_btn]:
        btn.setGraphicsEffect(None)
    buttons.addWidget(cancel_btn, 0)
    buttons.addWidget(submit_btn, 0)
    root_layout.addLayout(buttons)
    root_layout.addStretch(1)

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

    # --- Charging state (mengikuti login.py: #50B4FF saat charging) ---
    try:
        from ui.battery_status import get_battery_info
    except ImportError:
        from src.ui.battery_status import get_battery_info  # type: ignore

    from PySide6.QtCore import QTimer
    _charging_cache: dict[str, bool | None] = {"prev": None}

    def _apply_charging(charging: bool) -> None:
        dialog.setStyleSheet(_STYLE_CHARGING if charging else _STYLE_NORMAL)
        title.setText(_TITLE_CHARGING if charging else _TITLE_NORMAL)
        icon_color = QColor("#50B4FF") if charging else QColor("#FFFFFF")
        check_color = QColor("#50B4FF") if charging else QColor("#FFFFFF")
        eye_color = QColor("#50B4FF") if charging else QColor("#FFFFFF")
        label_color = QColor("#50B4FF") if charging else QColor("#FFFFFF")
        status_color = QColor("#50B4FF") if charging else QColor("#FFFFFF")

        # Update icon colors
        _set_icon(username_icon, _draw_user_icon(18, icon_color))
        _set_icon(password_icon, _draw_lock_icon(18, icon_color))
        _set_icon(status_icon, _draw_check_icon(16, check_color))
        toggle_password_btn.setIcon(QIcon(_draw_eye_icon(16, eye_color, crossed=False)))

        # Update label colors (username, password, status)
        username_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; letter-spacing: 0.8px; font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;")
        password_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; letter-spacing: 0.8px; font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;")
        status_text.setStyleSheet("color: #FFFFFF; font-size: 12px; font-family: 'SF Pro Display', 'SF Pro Text', Arial, sans-serif;")

        # Update glow/outline effect
        glow_color = QColor("#50B4FF" if charging else "#FFFFFF")
        glow_alpha = 120 if charging else 70
        for eff in [username_label.graphicsEffect(), password_label.graphicsEffect(), status_text.graphicsEffect()]:
            if isinstance(eff, QGraphicsDropShadowEffect):
                eff.setColor(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), glow_alpha))
                eff.setBlurRadius(12 if charging else 7)

        # Update tombol Cancel dan Sign In agar warna sesuai status charging
        # Selalu paksa kedua tombol menjadi primary (warna sama & efek sama) di semua state
        cancel_btn.primary = True
        submit_btn.primary = True
        for btn in [cancel_btn, submit_btn]:
            btn._custom_bg = None
            btn.setStyleSheet("border: none; background: transparent; font-weight: 700; font-family: 'SF Pro Display', Arial, sans-serif;")
            btn.update()

        # Update card shadow
        if charging:
            card_shadow.setBlurRadius(16)
            card_shadow.setOffset(3, 4)
            card_shadow.setColor(QColor(80, 180, 255, 130))
            if card.parentWidget():
                card.parentWidget().setGraphicsEffect(None)
        else:
            card_shadow.setBlurRadius(16)
            card_shadow.setOffset(3, 4)
            card_shadow.setColor(QColor(255, 255, 255, 60))
            # Aktifkan shadow biru kedua saat tidak charging
            if card.parentWidget():
                card_shadow2 = QGraphicsDropShadowEffect(card)
                card_shadow2.setBlurRadius(32)
                card_shadow2.setOffset(0, 0)
                card_shadow2.setColor(QColor(80, 180, 255, 40))
                card.parentWidget().setGraphicsEffect(card_shadow2)

        # Update shimmer Top Glow sesuai charging
        if hasattr(top_glow, 'setCharging'):
            top_glow.setCharging(charging)

    def _update_charging() -> None:
        info = get_battery_info()
        charging = bool(info.get("charging", False)) if info else False
        if _charging_cache["prev"] == charging:
            return
        _charging_cache["prev"] = charging
        _apply_charging(charging)

    _charging_timer = QTimer(dialog)
    _charging_timer.timeout.connect(_update_charging)
    _charging_timer.start(1000)
    _update_charging()  # update awal
    # -------------------------------------------------------------------

    username_input.setFocus()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result_user["user"]
    return None
