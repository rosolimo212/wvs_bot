from __future__ import annotations

from core.country_profiles import format_country_profile, load_country_profiles


def test_country_profiles_contains_rus() -> None:
    profiles = load_country_profiles()
    assert "RUS" in profiles
    assert profiles["RUS"]["full_name"] == "Россия"


def test_format_country_profile_renders_card() -> None:
    text = format_country_profile("RUS", "streamlit")
    assert "Россия" in text
    assert "Форма правления" in text
