import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from src.ui import boot


def _app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def test_acrylic_window_uses_shared_boot_dimensions() -> None:
    _app()
    window = boot.AcrylicWindow()

    try:
        assert window.width() == boot.BOOT_WIDTH
        assert window.height() == boot.BOOT_HEIGHT
        assert window._background_corner_radius == boot.BOOT_CORNER_RADIUS
        assert window.spinner.diameter == boot.SPINNER_DIAMETER
        assert window.globe_widget.width() == boot.GLOBE_DIAMETER
        assert window.globe_widget.height() == boot.GLOBE_DIAMETER
    finally:
        window.close()


def test_acrylic_window_fade_animations_use_shared_durations() -> None:
    _app()
    window = boot.AcrylicWindow()

    try:
        assert window._fade_in_anim.duration() == boot.BOOT_FADE_IN_MS
        assert window._fade_out_anim.duration() == boot.BOOT_FADE_OUT_MS

        window.setWindowOpacity(0.64)
        window.fade_out_and_accept()

        assert abs(window._fade_out_anim.startValue() - 0.64) < 0.01
    finally:
        window._fade_out_anim.stop()
        window.close()


def test_acrylic_window_charging_state_updates_visual_children(monkeypatch) -> None:
    _app()
    window = boot.AcrylicWindow()

    try:
        ui_module = types.ModuleType("ui")
        battery_module = types.ModuleType("ui.battery_status")
        battery_module.get_battery_info = lambda: {"charging": True}
        monkeypatch.setitem(sys.modules, "ui", ui_module)
        monkeypatch.setitem(sys.modules, "ui.battery_status", battery_module)

        window.update_charging_state()

        assert window._background_charging is True
        assert window.spinner.charging is True
        assert window.globe_widget.charging is True
    finally:
        window.close()


def test_spinner_uses_state_aware_motion_profile() -> None:
    _app()
    spinner = boot.CircularProgress(diameter=boot.SPINNER_DIAMETER)

    try:
        assert spinner.rotation_period == boot.SPINNER_IDLE_ROTATION_MS
        assert spinner.arc_anim_period == boot.SPINNER_IDLE_ARC_MS
        assert spinner.pulse_period == boot.SPINNER_IDLE_PULSE_MS

        spinner.set_charging(True)

        assert spinner.rotation_period == boot.SPINNER_CHARGING_ROTATION_MS
        assert spinner.arc_anim_period == boot.SPINNER_CHARGING_ARC_MS
        assert spinner.pulse_period == boot.SPINNER_CHARGING_PULSE_MS

        spinner.set_charging(False)

        assert spinner.rotation_period == boot.SPINNER_IDLE_ROTATION_MS
        assert spinner.arc_anim_period == boot.SPINNER_IDLE_ARC_MS
        assert spinner.pulse_period == boot.SPINNER_IDLE_PULSE_MS
    finally:
        spinner.close()


def test_acrylic_window_renders_nonblank_pixmap() -> None:
    app = _app()
    window = boot.AcrylicWindow()

    try:
        window.setWindowOpacity(1.0)
        window.show()
        app.processEvents()

        pixmap = QPixmap(window.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        window.render(pixmap)
        image = pixmap.toImage()

        sample_points = [
            (window.width() // 2, window.height() // 2),
            (window.width() // 2, window.height() // 3),
            (window.width() // 3, window.height() // 2),
            ((window.width() * 2) // 3, window.height() // 2),
        ]

        assert any(image.pixelColor(x, y).alpha() > 0 for x, y in sample_points)
    finally:
        window.close()
