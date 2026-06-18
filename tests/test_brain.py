from __future__ import annotations

from core.brain import match_menu_button, on_name_entered, on_start
from core.models import Screen


def test_on_start_screen() -> None:
    response = on_start("streamlit")
    assert response.screen == Screen.START
    assert "world values survey" in response.text.casefold()
    assert "зовут" in response.text.casefold()


def test_on_name_entered_has_five_menu_buttons() -> None:
    response = on_name_entered("Анна", "streamlit")
    assert response.screen == Screen.MAIN_MENU
    assert len(response.buttons) == 5


def test_on_name_entered_registration_greeting() -> None:
    response = on_name_entered("Анна", "streamlit", is_registration=True)
    assert "Приятно познакомиться" in response.text


def test_on_name_entered_return_greeting() -> None:
    response = on_name_entered("Анна", "streamlit", is_registration=False)
    assert "Рады, что вы вернулись" in response.text


def test_match_menu_button_learn_more() -> None:
    response = on_name_entered("Анна", "streamlit")
    matched = match_menu_button(response.buttons[0], "streamlit")
    assert matched == "learn_more"


def test_match_menu_button_option_1() -> None:
    response = on_name_entered("Анна", "streamlit")
    matched = match_menu_button(response.buttons[1], "streamlit")
    assert matched == "option_1"
