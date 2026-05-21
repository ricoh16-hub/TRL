"""Render premium padlock icon states for visual review.

Outputs:
  assets/padlock-lock-not-charging.png
  assets/padlock-unlock-not-charging.png
  assets/padlock-lock-charging.png
  assets/padlock-unlock-charging.png
  assets/padlock-icon-states.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QApplication

from ui.lock import _paint_premium_padlock


OUTPUT_DIR = ROOT / "assets"
SINGLE_SIZE = 128


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


def _render_single(path: Path, *, charging: bool, unlocked: bool) -> None:
    image = QImage(SINGLE_SIZE, SINGLE_SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    try:
        _paint_form_background(painter, QRectF(0, 0, SINGLE_SIZE, SINGLE_SIZE), charging)
        _paint_premium_padlock(
            painter,
            QRectF((SINGLE_SIZE - 64) / 2, 22, 64, 64),
            charging=charging,
            unlocked=unlocked,
            hovering=False,
            lock_color=QColor(255, 255, 255),
        )
    finally:
        painter.end()
    image.save(str(path))


def _render_sheet(path: Path) -> None:
    width = 520
    height = 180
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    try:
        _paint_form_background(painter, QRectF(0, 0, width / 2, height), False)
        _paint_form_background(painter, QRectF(width / 2, 0, width / 2, height), True)
        for x0, charging in ((26, False), (286, True)):
            for y, hovering in ((14, False), (94, True)):
                _paint_premium_padlock(
                    painter,
                    QRectF(x0, y, 64, 64),
                    charging=charging,
                    unlocked=False,
                    hovering=hovering,
                    lock_color=QColor(255, 255, 255),
                )
                _paint_premium_padlock(
                    painter,
                    QRectF(x0 + 72, y, 64, 64),
                    charging=charging,
                    unlocked=True,
                    hovering=hovering,
                    lock_color=QColor(255, 255, 255),
                )
    finally:
        painter.end()
    image.save(str(path))


def main() -> None:
    _app()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        (OUTPUT_DIR / "padlock-lock-not-charging.png", False, False),
        (OUTPUT_DIR / "padlock-unlock-not-charging.png", False, True),
        (OUTPUT_DIR / "padlock-lock-charging.png", True, False),
        (OUTPUT_DIR / "padlock-unlock-charging.png", True, True),
    ]
    for path, charging, unlocked in outputs:
        _render_single(path, charging=charging, unlocked=unlocked)
    _render_sheet(OUTPUT_DIR / "padlock-icon-states.png")
    for path, _, _ in outputs:
        print(path)
    print(OUTPUT_DIR / "padlock-icon-states.png")


if __name__ == "__main__":
    main()
