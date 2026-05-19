import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

from src.ui.credentials_login import (
    CredentialsGlassInputRow,
    CredentialsGlassStatusChip,
    CredentialsWarningDialog,
    LockReferenceCardPanel,
    PremiumCredentialsDialog,
    _apply_action_button_theme,
    _resolve_credentials_enter_action,
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
    assert cancel_btn._custom_gradient == submit_btn._custom_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient == submit_btn._custom_hover_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient == submit_btn._custom_border_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_border_gradient == submit_btn._custom_hover_border_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[0].name().lower() == "#2a3340"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#1b2431"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[0].name().lower() == "#36404f"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[1].name().lower() == "#242f3e"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[0].name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[0].alpha() == 132  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[1].name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[1].alpha() == 92  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[2].name().lower() == "#cdd8e4"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[2].alpha() == 46  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_border.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.alpha() == 104  # type: ignore[attr-defined]
    assert submit_btn._custom_border.alpha() == 104  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#ffffff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert submit_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
    assert submit_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
    assert cancel_btn.graphicsEffect() is not None
    assert submit_btn.graphicsEffect() is not None
    assert cancel_btn._custom_shadow == submit_btn._custom_shadow  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_shadow == submit_btn._custom_hover_shadow  # type: ignore[attr-defined]


def test_action_buttons_use_charging_palette() -> None:
    _get_app()
    cancel_btn = CustomButton("Cancel", primary=False)
    submit_btn = CustomButton("Sign In", primary=True)

    _apply_action_button_theme(cancel_btn, submit_btn, charging=True)

    assert cancel_btn.primary is False
    assert submit_btn.primary is False
    assert cancel_btn._custom_bg is None  # type: ignore[attr-defined]
    assert submit_btn._custom_bg is None  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient == submit_btn._custom_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient == submit_btn._custom_hover_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient == submit_btn._custom_border_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_border_gradient == submit_btn._custom_hover_border_gradient  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[0].name().lower() == "#162f40"  # type: ignore[attr-defined]
    assert cancel_btn._custom_gradient[1].name().lower() == "#124158"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[0].name().lower() == "#1c3d52"  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_gradient[1].name().lower() == "#185b7a"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[0].name().lower() == "#e8faff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[0].alpha() == 148  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[1].name().lower() == "#67e0ff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[1].alpha() == 126  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[2].name().lower() == "#378aee"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border_gradient[2].alpha() == 66  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.name().lower() == "#67e0ff"  # type: ignore[attr-defined]
    assert submit_btn._custom_border.name().lower() == "#67e0ff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_border.alpha() == 138  # type: ignore[attr-defined]
    assert submit_btn._custom_border.alpha() == 138  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_color.name().lower() == "#f7fcff"  # type: ignore[attr-defined]
    assert submit_btn._custom_text_color.name().lower() == "#f7fcff"  # type: ignore[attr-defined]
    assert cancel_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert submit_btn._custom_premium_surface is True  # type: ignore[attr-defined]
    assert cancel_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
    assert submit_btn._custom_text_shadow_color is not None  # type: ignore[attr-defined]
    assert cancel_btn._custom_shadow == submit_btn._custom_shadow  # type: ignore[attr-defined]
    assert cancel_btn._custom_hover_shadow == submit_btn._custom_hover_shadow  # type: ignore[attr-defined]


def test_action_button_hover_shadow_changes_only_hovered_button() -> None:
    app = _get_app()
    cancel_btn = CustomButton("Cancel", primary=False)
    submit_btn = CustomButton("Sign In", primary=True)

    _apply_action_button_theme(cancel_btn, submit_btn, charging=True)

    cancel_effect = cancel_btn.graphicsEffect()
    submit_effect = submit_btn.graphicsEffect()
    assert isinstance(cancel_effect, QGraphicsDropShadowEffect)
    assert isinstance(submit_effect, QGraphicsDropShadowEffect)
    assert cancel_effect.blurRadius() == submit_effect.blurRadius() == 17

    app.sendEvent(cancel_btn, QEvent(QEvent.Type.Enter))

    cancel_effect = cancel_btn.graphicsEffect()
    submit_effect = submit_btn.graphicsEffect()
    assert isinstance(cancel_effect, QGraphicsDropShadowEffect)
    assert isinstance(submit_effect, QGraphicsDropShadowEffect)
    assert cancel_effect.blurRadius() == 22
    assert submit_effect.blurRadius() == 17
    assert cancel_effect.color().name().lower() == "#1aa7e4"

    app.sendEvent(cancel_btn, QEvent(QEvent.Type.Leave))

    cancel_effect = cancel_btn.graphicsEffect()
    assert isinstance(cancel_effect, QGraphicsDropShadowEffect)
    assert cancel_effect.blurRadius() == 17


def test_credentials_enter_key_resolves_precise_primary_action() -> None:
    assert _resolve_credentials_enter_action("", "", "username") == (
        "focus_username",
        "Credentials Required",
        "Enter username and password to continue.",
    )
    assert _resolve_credentials_enter_action("operator", "", "username") == ("focus_password", "", "")
    assert _resolve_credentials_enter_action("operator", "", "password") == (
        "focus_password",
        "Password Required",
        "Enter password to continue.",
    )
    assert _resolve_credentials_enter_action("", "secret", "password") == (
        "focus_username",
        "Username Required",
        "Enter username to continue.",
    )
    assert _resolve_credentials_enter_action("operator", "secret", "form") == ("submit", "", "")


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


def test_credentials_inline_glass_surfaces_render_both_states() -> None:
    _get_app()
    input_row = CredentialsGlassInputRow()
    status_chip = CredentialsGlassStatusChip()
    input_row.resize(285, 41)
    status_chip.resize(285, 34)

    try:
        for widget in (input_row, status_chip):
            pixmap = QPixmap(widget.size())
            pixmap.fill(Qt.GlobalColor.transparent)
            widget.render(pixmap)
            image = pixmap.toImage()
            assert image.pixelColor(0, 0).alpha() == 0
            assert image.pixelColor(widget.width() - 1, 0).alpha() == 0
            assert image.pixelColor(widget.width() // 2, widget.height() // 2).alpha() > 0

            widget.set_charging(True)
            pixmap.fill(Qt.GlobalColor.transparent)
            widget.render(pixmap)
            image = pixmap.toImage()
            assert image.pixelColor(0, 0).alpha() == 0
            assert image.pixelColor(widget.width() // 2, widget.height() // 2).alpha() > 0

        input_row.set_focused(True)
        pixmap = QPixmap(input_row.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        input_row.render(pixmap)
        image = pixmap.toImage()
        assert image.pixelColor(input_row.width() // 2, input_row.height() // 2).alpha() > 0
    finally:
        input_row.close()
        status_chip.close()


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
