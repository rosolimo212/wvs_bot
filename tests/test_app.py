from __future__ import annotations

from core.app import AppService
from core.logging.noop import NoopLogger
from core.models import ACTION_OPTION_1, Screen, UserIdentity


def _noop_config() -> dict:
    return {
        "app": {"interface": "streamlit", "logging_enabled": False},
        "logging": {"schema": "wvs"},
        "telegram": {"token": ""},
    }


def test_handle_start_new_user() -> None:
    service = AppService(NoopLogger(), _noop_config())
    identity = UserIdentity(
        user_id="abc",
        internal_user_id=1,
        external_user_id="ext-1",
    )
    identity = service.logger.ensure_user("streamlit", "ext-1")
    response = service.handle_start(identity, "streamlit")
    assert response.screen == Screen.START


def test_handle_option_1_stub() -> None:
    service = AppService(NoopLogger(), _noop_config())
    identity = service.logger.ensure_user("streamlit", "ext-2")
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
