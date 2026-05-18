import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from src.ui.credentials_login import (
    CredentialsWarningDialog,
    LockReferenceCardPanel,
    PremiumCredentialsDialog,
    _apply_action_button_theme,
)
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
    assert cancel_btn._custom_gradient[0].name().lower() == "#242c38"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#19212c"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[0].name().lower() == "#303946"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[1].name().lower() == "#222b38"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[0].name().lower() == "#2d3644"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[1].name().lower() == "#202a37"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[0].name().lower() == "#3b4554"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[1].name().lower() == "#2b3544"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_border.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.alpha() == 62  # type: ignore[attr-defined]
    assert submit_btn._custom_border.alpha() == 108  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert submit_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
    assert submit_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
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
    assert cancel_btn._custom_gradient[0].name().lower() == "#222d3b"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#182230"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[0].name().lower() == "#223648"  # type: ignore[attr-defined]
    assert submit_btn._custom_gradient[1].name().lower() == "#194966"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[0].name().lower() == "#2b3848"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[1].name().lower() == "#1e2b3b"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[0].name().lower() == "#284258"  # type: ignore[attr-defined]
    assert submit_btn._custom_hover_gradient[1].name().lower() == "#225e80"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.name().lower() == "#ecfbff"  # type: ignore[attr-defined]
    assert submit_btn._custom_border.name().lower() == "#67e0ff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.alpha() == 66  # type: ignore[attr-defined]
    assert submit_btn._custom_border.alpha() == 132  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#f7fcff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#f7fcff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert submit_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
    assert submit_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]


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
    assert "QFrame#warningPanel" in dialog.styleSheet()
    assert "background: transparent" in dialog.styleSheet()
    assert "255, 255, 255" in dialog.styleSheet()

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

    assert "255, 255, 255" in dialog.styleSheet()
    dialog._set_charging(True)
    assert "80, 180, 255" in dialog.styleSheet()
    dialog._set_charging(False)
    assert "255, 255, 255" in dialog.styleSheet()


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


def test_pin_warning_dialog_uses_lock_reference_panel_and_renders() -> None:
    _get_app()
    parent = QWidget()
    parent.resize(405, 699)

    dialog = CredentialsWarningDialog(
        parent,
        "Incorrect PIN",
        "Incorrect PIN. Attempts remaining: 4.",
        charging=False,
        width=333,
        window_title="Security PIN",
        visual_mode="pin",
    )

    assert "QFrame#warningPanel" in dialog.styleSheet()
    assert "background: transparent" in dialog.styleSheet()

    try:
        pixmap = QPixmap(dialog.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        dialog.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(dialog.width() - 1, 0).alpha() == 0
        assert image.pixelColor(0, dialog.height() - 1).alpha() == 0
        assert image.pixelColor(dialog.width() - 1, dialog.height() - 1).alpha() == 0
        assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0

        dialog._set_charging(True)
        pixmap.fill(Qt.GlobalColor.transparent)
        dialog.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(dialog.width() - 1, 0).alpha() == 0
        assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0
    finally:
        dialog.close()


def test_credentials_warning_dialog_uses_lock_reference_panel_and_renders() -> None:
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

    try:
        pixmap = QPixmap(dialog.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        dialog.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(dialog.width() - 1, 0).alpha() == 0
        assert image.pixelColor(0, dialog.height() - 1).alpha() == 0
        assert image.pixelColor(dialog.width() - 1, dialog.height() - 1).alpha() == 0
        assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0

        dialog._set_charging(True)
        pixmap.fill(Qt.GlobalColor.transparent)
        dialog.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(dialog.width() - 1, 0).alpha() == 0
        assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0
    finally:
        dialog.close()


def test_lock_reference_card_panel_renders_both_states_with_rounded_corners() -> None:
    _get_app()
    panel = LockReferenceCardPanel(False)
    panel.resize(333, 236)

    try:
        pixmap = QPixmap(panel.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        panel.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(panel.width() - 1, 0).alpha() == 0
        assert image.pixelColor(0, panel.height() - 1).alpha() == 0
        assert image.pixelColor(panel.width() - 1, panel.height() - 1).alpha() == 0
        assert image.pixelColor(panel.width() // 2, panel.height() // 2).alpha() > 0

        panel.set_charging(True)
        pixmap.fill(Qt.GlobalColor.transparent)
        panel.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(panel.width() - 1, 0).alpha() == 0
        assert image.pixelColor(panel.width() // 2, panel.height() // 2).alpha() > 0
    finally:
        panel.close()


def test_premium_credentials_dialog_switches_and_renders_background() -> None:
    _get_app()
    dialog = PremiumCredentialsDialog()
    dialog.resize(405, 699)

    try:
        assert dialog._background_charging is False
        dialog.set_charging_background(True)
        assert dialog._background_charging is True

        pixmap = QPixmap(dialog.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        dialog.render(pixmap)
        image = pixmap.toImage()

        assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0
    finally:
        dialog.close()
