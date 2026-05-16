import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from src.ui.credentials_login import CredentialsWarningDialog, _apply_action_button_theme
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
    assert cancel_btn._custom_bg is None  # type: ignore[attr-defined]
    assert submit_btn._custom_bg is None  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_bg is None  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_bg is None  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[0].name().lower() == "#164f63"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#248fa0"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[0].name().lower() == "#164f63"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[1].name().lower() == "#248fa0"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[0].name().lower() == "#1e657a"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[1].name().lower() == "#35d6e7"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[0].name().lower() == "#1e657a"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[1].name().lower() == "#35d6e7"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.name().lower() == "#35d6e7"  # type: ignore[attr-defined]
    assert submit_btn._custom_border.name().lower() == "#35d6e7"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.alpha() == 145  # type: ignore[attr-defined]
    assert submit_btn._custom_border.alpha() == 145  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn.graphicsEffect() is not None
    assert submit_btn.graphicsEffect() is not None


def test_action_buttons_use_charging_palette() -> None:
    _get_app()
    cancel_btn = CustomButton("Cancel", primary=False)
    submit_btn = CustomButton("Sign In", primary=True)

    _apply_action_button_theme(cancel_btn, submit_btn, charging=True)

    assert cancel_btn.primary is False
    assert submit_btn.primary is False
    assert cancel_btn._custom_bg is None  # type: ignore[attr-defined]
    assert submit_btn._custom_bg is None  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[0].name().lower() == "#1f6faf"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#43a8e8"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[0].name().lower() == "#1f6faf"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[1].name().lower() == "#43a8e8"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[0].name().lower() == "#2b83c9"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[1].name().lower() == "#5bbeff"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[0].name().lower() == "#2b83c9"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[1].name().lower() == "#5bbeff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.name().lower() == "#69c3ff"  # type: ignore[attr-defined]
    assert submit_btn._custom_border.name().lower() == "#69c3ff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.alpha() == 165  # type: ignore[attr-defined]
    assert submit_btn._custom_border.alpha() == 165  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]


def test_credentials_warning_dialog_matches_card_width() -> None:
    _get_app()
    parent = QWidget()
    parent.resize(405, 699)

    dialog = CredentialsWarningDialog(
        parent,
        "Sign In Failed",
        "Check your username and password.",
        charging=False,
        width=333,
    )

    assert dialog.objectName() == "credentialsWarningDialog"
    assert dialog.width() == 333
    assert dialog.height() == CredentialsWarningDialog.HEIGHT
    assert "#10263D" in dialog.styleSheet()
    assert "#24445F" in dialog.styleSheet()

    close_btn = dialog.findChild(QWidget, "warningClose")
    assert close_btn is not None
    assert close_btn.toolTip() == "Close"
    assert close_btn.accessibleName() == "Close"
    assert close_btn.focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_credentials_warning_dialog_supports_charging_palette() -> None:
    _get_app()
    parent = QWidget()
    parent.resize(405, 699)

    dialog = CredentialsWarningDialog(
        parent,
        "Credentials Required",
        "Enter your username and password.",
        charging=True,
        width=333,
    )

    assert dialog.objectName() == "credentialsWarningDialog"
    assert dialog.width() == 333
    assert dialog.height() == CredentialsWarningDialog.HEIGHT
    assert "#50B4FF" not in dialog.styleSheet()
    assert "80, 180, 255" in dialog.styleSheet()


def test_credentials_warning_dialog_can_switch_palette_after_opening() -> None:
    _get_app()
    parent = QWidget()
    parent.resize(405, 699)

    dialog = CredentialsWarningDialog(
        parent,
        "Sign In Failed",
        "Check your username and password.",
        charging=False,
        width=333,
    )

    assert "53, 214, 231" in dialog.styleSheet()
    dialog._set_charging(True)
    assert "80, 180, 255" in dialog.styleSheet()
    dialog._set_charging(False)
    assert "53, 214, 231" in dialog.styleSheet()


def test_credentials_warning_dialog_enforces_minimum_width() -> None:
    _get_app()
    parent = QWidget()
    parent.resize(405, 699)

    dialog = CredentialsWarningDialog(
        parent,
        "Sign In Failed",
        "Check your username and password.",
        charging=False,
        width=100,
    )

    assert dialog.width() == CredentialsWarningDialog.WIDTH_MIN
