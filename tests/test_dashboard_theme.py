from src.ui.dashboard import (
    CHARGING_ACCENT,
    NAVY_SELECTED,
    NAVY_TOP,
    _charging_theme_palette,
    _resolve_charging_state,
)


def test_resolve_charging_state_handles_missing_info() -> None:
    assert _resolve_charging_state(None) is False
    assert _resolve_charging_state({}) is False


def test_resolve_charging_state_reads_boolean_flag() -> None:
    assert _resolve_charging_state({"charging": True}) is True
    assert _resolve_charging_state({"charging": False}) is False


def test_charging_theme_palette_for_charging_mode() -> None:
    palette = _charging_theme_palette(True)

    assert palette["accent"] == CHARGING_ACCENT
    assert palette["hover"] == "#3AA8F5"
    assert palette["pressed"] == "#2A96E0"
    assert palette["badge_label"] == "Charging Mode"


def test_charging_theme_palette_for_standard_mode() -> None:
    palette = _charging_theme_palette(False)

    assert palette["accent"] == NAVY_TOP
    assert palette["hover"] == NAVY_SELECTED
    assert palette["pressed"] == "#0e2847"
    assert palette["badge_label"] == "Standard Mode"