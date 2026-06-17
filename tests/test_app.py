from __future__ import annotations

from core.app import AppService
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button, button, message, return_later_button
from core.models import ACTION_MAIN_ANSWER, ACTION_OPTION_1, ACTION_OPTION_2, ACTION_SECONDARY_ANSWER, Screen
from core.questionnaire.loader import load_questions
from core.questionnaire.memory import MemoryMainAnswerStore, MemorySecondaryAnswerStore


def _service() -> AppService:
    root_questions = load_questions("questions.json")
    return AppService(
        NoopLogger(),
        {
            "app": {"interface": "streamlit", "logging_enabled": False},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
        questions_data=root_questions,
    )


def _register(service: AppService, identity):
    return service.handle_action(
        identity,
        "streamlit",
        "name_entered",
        {"text": "Роман"},
    )


def test_handle_start_new_user() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-1")
    response = service.handle_start(identity, "streamlit")
    assert response.screen == Screen.START


def test_handle_option_1_shows_first_question() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-2")
    _register(service, identity)
    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_1,
        {"user_name": "Роман"},
    )
    assert response.screen == Screen.MAIN_QUESTIONARY
    assert "Вопрос 1" in response.text
    assert button("return_later", "streamlit") in response.buttons


def test_main_questionary_resume_after_answer() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-3")
    _register(service, identity)
    service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_1,
        {"user_name": "Роман"},
    )
    first_variant = service._main_questions[0]["variants"][0]
    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_MAIN_ANSWER,
        {
            "user_name": "Роман",
            "selected": first_variant,
            "answer": first_variant,
        },
    )
    assert response.screen == Screen.MAIN_QUESTIONARY
    assert "Вопрос 2" in response.text
    assert button("custom_answer", "streamlit") not in response.buttons


def test_text_question_uses_input_mode_text() -> None:
    service = _service()
    q8 = service._main_questions[7]
    from core.brain import on_main_question_show
    from core.questionnaire.loader import question_input_mode

    assert question_input_mode(q8) == "text"
    shown = on_main_question_show(q8, remaining=6, channel="streamlit")
    assert shown.meta["input_mode"] == "text"
    assert button("custom_answer", "streamlit") not in shown.buttons


def test_option_3_locked_logs_find_country_start() -> None:
    from core.logging.noop import NoopLogger

    class RecordingLogger(NoopLogger):
        def __init__(self) -> None:
            super().__init__()
            self.events: list[str] = []
            self.event_parameters: list[dict] = []

        def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
            self.events.append(event_name)
            self.event_parameters.append(event_parameters or {})

    logger = RecordingLogger()
    service = AppService(
        logger,
        {
            "app": {"interface": "telegram", "logging_enabled": True},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
    )
    identity = logger.ensure_user("telegram", "locked-3")
    service.handle_action(identity, "telegram", "name_entered", {"text": "Иван"})
    response = service.handle_action(
        identity,
        "telegram",
        "option_3",
        {"user_name": "Иван"},
    )
    assert message("feature_locked", "telegram") in response.text
    assert "find_counry_start" in logger.events
    idx = logger.events.index("find_counry_start")
    assert logger.event_parameters[idx]["answer"] == response.text


def test_option_4_locked_logs_find_own_place_start() -> None:
    from core.logging.noop import NoopLogger

    class RecordingLogger(NoopLogger):
        def __init__(self) -> None:
            super().__init__()
            self.events: list[str] = []
            self.event_parameters: list[dict] = []

        def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
            self.events.append(event_name)
            self.event_parameters.append(event_parameters or {})

    logger = RecordingLogger()
    service = AppService(
        logger,
        {
            "app": {"interface": "telegram", "logging_enabled": True},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
    )
    identity = logger.ensure_user("telegram", "locked-4")
    service.handle_action(identity, "telegram", "name_entered", {"text": "Иван"})
    response = service.handle_action(
        identity,
        "telegram",
        "option_4",
        {"user_name": "Иван"},
    )
    assert message("feature_locked", "telegram") in response.text
    assert "find_own_place_start" in logger.events
    idx = logger.events.index("find_own_place_start")
    assert logger.event_parameters[idx]["answer"] == response.text


def test_option_3_locked_until_complete() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-4")
    _register(service, identity)
    locked = service.handle_action(
        identity,
        "streamlit",
        "option_3",
        {"user_name": "Роман"},
    )
    assert message("feature_locked", "streamlit") in locked.text

    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {
                "user_name": "Роман",
                "selected": variant,
                "answer": variant,
            },
        )

    unlocked = service.handle_action(
        identity,
        "streamlit",
        "option_3",
        {"user_name": "Роман"},
    )
    assert message("analytics_no_data", "streamlit") in unlocked.text
    assert unlocked.screen == Screen.FIND_COUNTRY


def test_return_later_goes_to_main_menu() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-5")
    _register(service, identity)
    service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_1,
        {"user_name": "Роман"},
    )
    response = service.handle_action(
        identity,
        "streamlit",
        "main_return_later",
        {"user_name": "Роман"},
    )
    assert response.screen == Screen.MAIN_MENU


def test_main_complete_shows_indices() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-complete")
    _register(service, identity)
    service.handle_action(identity, "streamlit", ACTION_OPTION_1, {"user_name": "Роман"})

    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {
                "user_name": "Роман",
                "selected": variant,
                "answer": variant,
            },
        )

    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_1,
        {"user_name": "Роман"},
    )
    assert response.screen == Screen.MAIN_MENU
    assert message("main_questionary_complete_intro", "streamlit") in response.text
    assert "традиционных/секулярных" in response.text
    assert message("main_questionary_complete_outro", "streamlit") in response.text


def test_option_2_starts_secondary_questionary() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-secondary")
    _register(service, identity)
    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_2,
        {"user_name": "Роман"},
    )
    assert response.screen == Screen.SECONDARY_QUESTIONARY
    assert "дополнительную анкету" in response.text
    assert service._secondary_questions[0]["text"] in response.text
    assert response.text.count("Осталось 14 вопросов") == 1


def test_secondary_questionary_resume_after_answer() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-secondary-2")
    _register(service, identity)
    service.handle_action(identity, "streamlit", ACTION_OPTION_2, {"user_name": "Роман"})
    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_SECONDARY_ANSWER,
        {
            "user_name": "Роман",
            "selected": "",
            "answer": "1990",
        },
    )
    assert response.screen == Screen.SECONDARY_QUESTIONARY
    assert "Вопрос 2" in response.text
