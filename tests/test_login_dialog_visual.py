import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from ui.login import LoginDialog


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_login_dialog_switches_and_renders_lock_style_background() -> None:
    _get_app()
    dialog = LoginDialog()
    dialog.resize(405, 699)

    try:
        assert dialog._background_charging is False
        dialog.set_background_charging(True)
        assert dialog._background_charging is True

        pixmap = QPixmap(dialog.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        dialog.render(pixmap)
        image = pixmap.toImage()

        assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0
    finally:
        dialog.close()
