from __future__ import annotations

from core.app import AppService
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button, message
from core.models import ACTION_OPTION_1, Screen


def _noop_config() -> dict:
    return {
        "app": {"interface": "streamlit", "logging_enabled": False},
        "logging": {"schema": "wvs"},
        "telegram": {"token": ""},
    }


def test_handle_start_new_user() -> None:
    service = AppService(NoopLogger(), _noop_config())
    identity = service.logger.ensure_user("streamlit", "ext-1")
    response = service.handle_start(identity, "streamlit")
    assert response.screen == Screen.START


def test_handle_option_stub_same_text_for_all() -> None:
    service = AppService(NoopLogger(), _noop_config())
    identity = service.logger.ensure_user("streamlit", "ext-2")
    service.handle_action(
        identity,
        "streamlit",
        "name_entered",
        {"text": "Роман"},
    )
    expected_text = message("feature_stub", "streamlit")
    back_btn = back_to_menu_button("streamlit")

    for action in ("option_1", "option_2", "option_3", "option_4"):
        response = service.handle_action(
            identity,
            "streamlit",
            action,
            {"user_name": "Роман"},
        )
        assert response.text == expected_text
        assert response.buttons == [back_btn]


def test_handle_option_1_screen() -> None:
    service = AppService(NoopLogger(), _noop_config())
    identity = service.logger.ensure_user("streamlit", "ext-3")
    service.handle_action(
        identity,
        "streamlit",
        "name_entered",
        {"text": "Роман"},
    )
    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_1,
        {"user_name": "Роман"},
    )
    assert response.screen == Screen.MAIN_QUESTIONARY
