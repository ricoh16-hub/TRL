import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.ui.credentials_login import _apply_action_button_theme
from src.ui.custom_button import CustomButton


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_action_buttons_use_non_charging_palette() -> None:
    _get_app()
    cancel_btn = CustomButton("Cancel", primary=False)
    submit_btn = CustomButton("Sign In", primary=True)

    _apply_action_button_theme(cancel_btn, submit_btn, charging=False)

    assert cancel_btn.primary is False
    assert submit_btn.primary is False
    assert cancel_btn._custom_bg.name().lower() == "#f5f3f1"  # type: ignore[attr-defined]
    assert submit_btn._custom_bg.name().lower() == "#f5f3f1"  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#163a72"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#163a72"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient is None  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient is None  # type: ignore[attr-defined]


def test_action_buttons_use_charging_palette() -> None:
    _get_app()
    cancel_btn = CustomButton("Cancel", primary=False)
    submit_btn = CustomButton("Sign In", primary=True)

    _apply_action_button_theme(cancel_btn, submit_btn, charging=True)

    assert cancel_btn.primary is False
    assert submit_btn.primary is False
    assert cancel_btn._custom_bg is None  # type: ignore[attr-defined]
    assert submit_btn._custom_bg is None  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[0].name().lower() == "#2c89db"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#58bcff"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[0].name().lower() == "#2c89db"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[1].name().lower() == "#58bcff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
