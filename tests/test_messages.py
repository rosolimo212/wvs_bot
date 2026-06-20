from __future__ import annotations

from core.messages import menu_buttons, message


def test_message_start_ask_name() -> None:
    text = message("start_ask_name", "streamlit")
    assert "запомним" in text.casefold()


def test_message_start_intro() -> None:
    text = message("start_intro", "streamlit")
    assert "привет" in text.casefold()
    assert "world values survey" in text.casefold()
    assert "инглхарат" in text.casefold()


def test_menu_buttons_count() -> None:
    assert len(menu_buttons("streamlit")) == 5
