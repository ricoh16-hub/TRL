import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from ui.lock import _paint_premium_padlock


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _render_padlock(*, charging: bool, unlocked: bool, hovering: bool = False) -> QImage:
    _get_app()
    image = QImage(96, 96, QImage.Format.Format_ARGB32_Premultiplied)
    background = QColor(20, 36, 55) if charging else QColor(31, 39, 50)
    image.fill(background)
    painter = QPainter(image)
    try:
        _paint_premium_padlock(
            painter,
            QRectF(16.0, 10.0, 64.0, 64.0),
            charging=charging,
            unlocked=unlocked,
            hovering=hovering,
            lock_color=QColor(255, 255, 255),
        )
    finally:
        painter.end()
    return image


def _average_rgb(image: QImage, rect: tuple[int, int, int, int]) -> tuple[float, float, float]:
    x, y, width, height = rect
    pixels = []
    for px in range(x, x + width):
        for py in range(y, y + height):
            color = image.pixelColor(px, py)
            pixels.append((color.red(), color.green(), color.blue()))
    count = float(len(pixels))
    return (
        sum(pixel[0] for pixel in pixels) / count,
        sum(pixel[1] for pixel in pixels) / count,
        sum(pixel[2] for pixel in pixels) / count,
    )


def _mean_abs_diff(
    left: QImage,
    right: QImage,
    rect: tuple[int, int, int, int] | None = None,
) -> float:
    total = 0
    samples = 0
    if rect is None:
        x0, y0 = 0, 0
        x1, y1 = min(left.width(), right.width()), min(left.height(), right.height())
    else:
        x0, y0, width, height = rect
        x1, y1 = x0 + width, y0 + height
    for x in range(x0, x1, 2):
        for y in range(y0, y1, 2):
            lc = left.pixelColor(x, y)
            rc = right.pixelColor(x, y)
            total += abs(lc.red() - rc.red())
            total += abs(lc.green() - rc.green())
            total += abs(lc.blue() - rc.blue())
            samples += 3
    return total / float(samples)


def test_premium_padlock_renders_all_states_distinctly() -> None:
    normal_lock = _render_padlock(charging=False, unlocked=False)
    normal_unlock = _render_padlock(charging=False, unlocked=True)
    charging_lock = _render_padlock(charging=True, unlocked=False)
    charging_unlock = _render_padlock(charging=True, unlocked=True)

    shackle_rect = (38, 23, 28, 28)
    assert _mean_abs_diff(normal_lock, normal_unlock, shackle_rect) > 1.1
    assert _mean_abs_diff(charging_lock, charging_unlock, shackle_rect) > 1.1
    assert _mean_abs_diff(normal_lock, charging_lock) > 5.0
    assert _mean_abs_diff(normal_unlock, charging_unlock) > 5.0


def test_premium_padlock_color_tracks_background_theme() -> None:
    normal_lock = _render_padlock(charging=False, unlocked=False)
    charging_lock = _render_padlock(charging=True, unlocked=False)

    normal_r, normal_g, normal_b = _average_rgb(normal_lock, (39, 45, 18, 18))
    charging_r, charging_g, charging_b = _average_rgb(charging_lock, (39, 45, 18, 18))

    assert abs(normal_r - normal_g) < 18
    assert abs(normal_g - normal_b) < 26
    assert charging_b > charging_r + 24
    assert charging_g > charging_r + 18


def test_premium_padlock_hover_adds_subtle_glow_without_changing_material() -> None:
    base = _render_padlock(charging=True, unlocked=True, hovering=False)
    hover = _render_padlock(charging=True, unlocked=True, hovering=True)

    assert _mean_abs_diff(base, hover) > 0.2
    assert _mean_abs_diff(base, hover) < 6.0
