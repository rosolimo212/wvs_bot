from __future__ import annotations

from core.app import AppService
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button


class RecordingLogger(NoopLogger):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
        self.events.append(event_name)


def _noop_config() -> dict:
    return {
        "app": {"interface": "streamlit", "logging_enabled": False},
        "logging": {"schema": "wvs"},
        "telegram": {"token": ""},
    }


def test_back_to_menu_logs_click_then_visit() -> None:
    logger = RecordingLogger()
    service = AppService(logger, _noop_config())
    identity = logger.ensure_user("streamlit", "ext-back")

    service.handle_action(
        identity,
        "streamlit",
        "name_entered",
        {"text": "Роман"},
    )
    service.handle_action(
        identity,
        "streamlit",
        "option_1",
        {"user_name": "Роман"},
    )
    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "user_name": "Роман",
            "text": back_to_menu_button("streamlit"),
            "screen": "main_questionary",
        },
    )

    assert logger.events[-2:] == ["main_menu_click", "main_menu_visit"]
