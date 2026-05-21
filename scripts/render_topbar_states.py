"""Render top-bar states for lock and login visual review."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from ui.lock import (
    TOP_BAR_CENTER_ICON_SIZE,
    BatteryLogoWidget,
    GearIconWidget,
    KeyCapWidget,
    WiFiLogoWidget,
    CustomLockIcon,
    calculate_top_bar_layout,
)
from ui.login import CustomUnlockIcon


OUTPUT = ROOT / "assets" / "topbar-states.png"
FORM_WIDTH = 405
PANEL_HEIGHT = 86


class SegmentClock(QWidget):
    SEGMENTS = {
        "0": "abcedf",
        "1": "bc",
        "2": "abged",
        "3": "abgcd",
        "4": "fgbc",
        "5": "afgcd",
        "6": "afgecd",
        "7": "abc",
        "8": "abcdefg",
        "9": "abfgcd",
    }

    def __init__(self, text: str, *, charging: bool, parent: QWidget) -> None:
        super().__init__(parent)
        self.text = text
        self.charging = charging
        self.setFixedSize(58, 30)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(80, 180, 255, 224) if self.charging else QColor(240, 244, 250, 226)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        x = 1.0
        for char in self.text:
            if char == ".":
                painter.drawEllipse(QRectF(x + 1.6, 19.0, 2.4, 2.4))
                x += 5.0
                continue
            self._draw_digit(painter, x, 5.0, char)
            x += 10.8
        painter.end()

    def _draw_digit(self, painter: QPainter, x: float, y: float, char: str) -> None:
        active = self.SEGMENTS.get(char, "")
        thickness = 1.45
        width = 7.4
        height = 18.0
        mid_y = y + height / 2.0
        segments = {
            "a": QRectF(x + 1.2, y, width - 2.4, thickness),
            "b": QRectF(x + width - thickness, y + 1.1, thickness, height / 2.0 - 2.0),
            "c": QRectF(x + width - thickness, mid_y + 0.9, thickness, height / 2.0 - 2.0),
            "d": QRectF(x + 1.2, y + height - thickness, width - 2.4, thickness),
            "e": QRectF(x, mid_y + 0.9, thickness, height / 2.0 - 2.0),
            "f": QRectF(x, y + 1.1, thickness, height / 2.0 - 2.0),
            "g": QRectF(x + 1.2, mid_y - thickness / 2.0, width - 2.4, thickness),
        }
        for name, rect in segments.items():
            if name in active:
                painter.drawRoundedRect(rect, 0.7, 0.7)


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _paint_form_background(painter: QPainter, rect: QRectF, charging: bool) -> None:
    gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    if charging:
        gradient.setColorAt(0.0, QColor(18, 30, 43))
        gradient.setColorAt(0.48, QColor(31, 47, 64))
        gradient.setColorAt(1.0, QColor(20, 36, 55))
    else:
        gradient.setColorAt(0.0, QColor(26, 32, 41))
        gradient.setColorAt(0.48, QColor(41, 49, 60))
        gradient.setColorAt(1.0, QColor(31, 39, 50))
    painter.fillRect(rect, QBrush(gradient))


def _render_panel(*, login: bool, charging: bool) -> QWidget:
    panel = QWidget()
    panel.setFixedSize(FORM_WIDTH, PANEL_HEIGHT)
    panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    battery = BatteryLogoWidget(panel)
    battery.timer.stop()
    battery.charging = charging
    battery.battery_level = 1.0
    battery.battery_percent = 100

    keycap = KeyCapWidget(panel, text="A", battery_widget=battery)
    if hasattr(keycap, "_keyboard_timer"):
        keycap._keyboard_timer.stop()
    wifi = WiFiLogoWidget(panel, battery_widget=battery)
    wifi._wifi_timer.stop()
    wifi._wifi_name = "Connected"

    gear = None
    clock = None
    if login:
        clock = SegmentClock("14.58", charging=charging, parent=panel)
        center_icon = CustomUnlockIcon(QColor(255, 255, 255), parent=panel, charging=charging)
        center_icon.set_battery_widget(battery)
        layout = calculate_top_bar_layout(
            form_width=FORM_WIDTH,
            center_icon_width=TOP_BAR_CENTER_ICON_SIZE,
            keycap_width=keycap.width(),
            keycap_height=keycap.height(),
            battery_height=battery.height(),
            wifi_height=wifi.height(),
            clock_width=clock.width(),
            clock_height=clock.height(),
        )
    else:
        gear = GearIconWidget(panel)
        gear.set_battery_widget(battery)
        center_icon = CustomLockIcon(QColor(255, 255, 255), parent=panel, charging=charging)
        center_icon.battery_widget = battery
        layout = calculate_top_bar_layout(
            form_width=FORM_WIDTH,
            center_icon_width=TOP_BAR_CENTER_ICON_SIZE,
            keycap_width=keycap.width(),
            keycap_height=keycap.height(),
            battery_height=battery.height(),
            wifi_height=wifi.height(),
            gear_width=gear.width(),
            gear_height=gear.height(),
            gear_visual_size=gear.getGearSize(),
        )

    battery.move(layout["battery_x"], layout["battery_y"])
    battery.show()
    keycap.move(layout["keycap_x"], layout["keycap_y"])
    keycap.show()
    if login:
        assert clock is not None
        clock.move(layout["clock_x"], layout["clock_y"])
        clock.show()
    else:
        assert gear is not None
        gear.move(layout["gear_x"], layout["gear_y"])
        gear.show()

    center_icon.move(layout["center_x"], layout["center_y"])
    center_icon.show()

    wifi.move(layout["wifi_x"], layout["wifi_y"])
    wifi.show()

    return panel


def main() -> None:
    _app()
    image = QImage(FORM_WIDTH * 2, PANEL_HEIGHT * 2, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    try:
        panels = [
            (0, 0, False, False),
            (FORM_WIDTH, 0, False, True),
            (0, PANEL_HEIGHT, True, False),
            (FORM_WIDTH, PANEL_HEIGHT, True, True),
        ]
        for x, y, login, charging in panels:
            rect = QRectF(x, y, FORM_WIDTH, PANEL_HEIGHT)
            _paint_form_background(painter, rect, charging)
            panel = _render_panel(login=login, charging=charging)
            panel.render(painter, QPoint(x, y))
            panel.close()
    finally:
        painter.end()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(OUTPUT))
    print(OUTPUT)


if __name__ == "__main__":
    main()
