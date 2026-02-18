from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QTransform, QColor
from PySide6.QtWidgets import QApplication
from auth.login import authenticate

GLASS_STYLE = """
QDialog {
	background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
		stop:0 #ffffffcc, stop:1 #aeefffcc);
	border-radius: 24px;
	border: 1px solid rgba(255,255,255,0.18);
	backdrop-filter: blur(18px);
}
QLineEdit {
	color: #222a36;
	font-family: 'SF Pro Display', 'San Francisco', 'Arial', sans-serif;
	font-size: 16px;
	background: rgba(255,255,255,0.18);
	border-radius: 12px;
	border: 1px solid rgba(255,255,255,0.10);
	padding: 8px 16px;
	margin-bottom: 12px;
}
QPushButton {
	background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
		stop:0 #aeefff, stop:1 #5f8cff);
	color: #fff;
	border-radius: 12px;
	font-size: 16px;
	font-weight: 600;
	padding: 8px 24px;
	border: none;
	opacity: 0.92;
	font-family: 'SF Pro Display', 'San Francisco', 'Arial', sans-serif;
}
QPushButton:hover {
	background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
		stop:0 #5f8cff, stop:1 #aeefff);
}
"""

class LockIcon(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setFixedSize(80, 80)
		self._scale = 1.0
		self._shackle_angle = 0
		self.hover_anim = QPropertyAnimation(self, b"scale")
		self.hover_anim.setDuration(220)
		self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
		self.shackle_anim = QPropertyAnimation(self, b"shackle_angle")
		self.shackle_anim.setDuration(400)
		self.shackle_anim.setEasingCurve(QEasingCurve.Type.OutBack)
		self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

	def mousePressEvent(self, event):
		self.unlock()
		event.accept()
		super().__init__(parent)
		self.setFixedSize(80, 80)
		self._scale = 1.0
		self._shackle_angle = 0
		self.hover_anim = QPropertyAnimation(self, b"scale")
		self.hover_anim.setDuration(220)
		self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
		self.shackle_anim = QPropertyAnimation(self, b"shackle_angle")
		self.shackle_anim.setDuration(400)
		self.shackle_anim.setEasingCurve(QEasingCurve.Type.OutBack)
		self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

	def enterEvent(self, event):
		self.hover_anim.stop()
		self.hover_anim.setStartValue(self._scale)
		self.hover_anim.setEndValue(1.13)
		self.hover_anim.start()

	def leaveEvent(self, event):
		self.hover_anim.stop()
		self.hover_anim.setStartValue(self._scale)
		self.hover_anim.setEndValue(1.0)
		self.hover_anim.start()

	def unlock(self):
		self.shackle_anim.stop()
		self.shackle_anim.setStartValue(0)
		self.shackle_anim.setEndValue(38)
		self.shackle_anim.start()

	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.save()
		# Center and scale
		painter.translate(self.width() / 2, self.height() / 2)
		painter.scale(self._scale, self._scale)
		painter.translate(-self.width() / 2, -self.height() / 2)
		# Draw body only (no outline, no shackle)
		body_color = QColor(60, 60, 80, 220)
		painter.setBrush(body_color)
		painter.setPen(Qt.NoPen)
		# Jika tidak hover, tambah bagian bawah body
		if self._scale == 1.0:
			painter.drawRoundedRect(20, 38, 40, 48, 12, 12)
		else:
			painter.drawRoundedRect(20, 38, 40, 42, 12, 12)
		painter.restore()

	def get_scale(self):
		return self._scale
	def set_scale(self, value):
		self._scale = value
		self.update()
	scale = Property(float, get_scale, set_scale)

	def get_shackle_angle(self):
		return self._shackle_angle
	def set_shackle_angle(self, value):
		self._shackle_angle = value
		self.update()
	shackle_angle = Property(float, get_shackle_angle, set_shackle_angle)

def show_login(app: QApplication) -> None:
	dialog = QDialog()
	dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
	width_px = int(10.5 * 0.3937 * 96)
	height_px = int(18.5 * 0.3937 * 96)
	dialog.setFixedSize(width_px, height_px)
	screen = app.primaryScreen()
	screen_geometry = screen.geometry()
	x = screen_geometry.x() + (screen_geometry.width() - width_px) // 2
	y = screen_geometry.y() + (screen_geometry.height() - height_px) // 2
	dialog.move(x, y)
	dialog.setStyleSheet(GLASS_STYLE)

	layout = QVBoxLayout()
	layout.setContentsMargins(0, 0, 0, 0)
	layout.setSpacing(0)

	# Lock Icon
	lock_icon = LockIcon(dialog)
	layout.addWidget(lock_icon, alignment=Qt.AlignmentFlag.AlignHCenter)

	# Username
	username = QLineEdit()
	username.setPlaceholderText('Username')
	username.setAlignment(Qt.AlignmentFlag.AlignCenter)
	layout.addWidget(username)

	# Password
	password = QLineEdit()
	password.setPlaceholderText('Password')
	password.setEchoMode(QLineEdit.EchoMode.Password)
	password.setAlignment(Qt.AlignmentFlag.AlignCenter)
	layout.addWidget(password)

	# Login Button
	login_btn = QPushButton('Login')
	layout.addWidget(login_btn)

	dialog.setLayout(layout)

	def on_login():
		# Trigger unlock animation
		lock_icon.unlock()
		authenticate(username.text(), password.text())

	login_btn.clicked.connect(on_login)
	dialog.exec()