from src.ui.dashboard import (
    CHARGING_ACCENT,
    _charging_theme_palette,
    _resolve_charging_state,
)


def test_resolve_charging_state_handles_missing_info() -> None:
    assert _resolve_charging_state(None) is False
    assert _resolve_charging_state({}) is False


def test_resolve_charging_state_reads_boolean_flag() -> None:
    assert _resolve_charging_state({"charging": True}) is True
    assert _resolve_charging_state({"charging": False}) is False


def test_resolve_charging_state_reads_integer_flag() -> None:
    assert _resolve_charging_state({"charging": 1}) is True
    assert _resolve_charging_state({"charging": 0}) is False


def test_charging_theme_palette_for_charging_mode() -> None:
    palette = _charging_theme_palette(True)

    assert palette["accent"] == CHARGING_ACCENT
    assert palette["hover"] == "#3AA8F5"
    assert palette["pressed"] == "#2A96E0"
    assert palette["badge_label"] == "Charging Mode"


def test_charging_theme_palette_for_standard_mode() -> None:
    palette = _charging_theme_palette(False)

    assert palette["accent"] == "#FFFFFF"
    assert palette["hover"] == "#DDE6F2"
    assert palette["pressed"] == "#AEBBCC"
    assert palette["badge_label"] == "Standard Mode"
