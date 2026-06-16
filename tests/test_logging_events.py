from __future__ import annotations

from core.app import AppService
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button, button
from core.models import ACTION_OPTION_2
from core.questionnaire.memory import MemoryMainAnswerStore


class RecordingLogger(NoopLogger):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []
        self.event_parameters: list[dict] = []

    def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
        self.events.append(event_name)
        self.event_parameters.append(event_parameters or {})


def _service(logger: RecordingLogger) -> AppService:
    return AppService(
        logger,
        {
            "app": {"interface": "streamlit", "logging_enabled": False},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
        },
        answer_store=MemoryMainAnswerStore(),
    )


def test_back_to_menu_logs_click_then_visit() -> None:
    logger = RecordingLogger()
    service = _service(logger)
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
        ACTION_OPTION_2,
        {"user_name": "Роман"},
    )
    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "user_name": "Роман",
            "text": back_to_menu_button("streamlit"),
            "screen": "secondary_questionary",
        },
    )

    assert logger.events[-2:] == ["main_menu_click", "main_menu_visit"]


def test_main_questionary_logs_question_and_answer() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-q")

    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})
    service.handle_action(identity, "streamlit", "option_1", {"user_name": "Роман"})
    assert "main_questionary_start" in logger.events
    assert "question_show" in logger.events

    first_variant = service._main_questions[0]["variants"][0]
    service.handle_action(
        identity,
        "streamlit",
        "main_answer",
        {
            "user_name": "Роман",
            "selected": first_variant,
            "answer": first_variant,
        },
    )
    assert "answer_sent" in logger.events
    answer_events = [
        params
        for name, params in zip(logger.events, logger.event_parameters, strict=False)
        if name == "answer_sent"
    ]
    assert answer_events[-1]["answer"] == first_variant
