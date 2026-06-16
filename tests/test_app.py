from __future__ import annotations

from core.app import AppService
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button, button, message, return_later_button
from core.models import ACTION_MAIN_ANSWER, ACTION_OPTION_1, Screen
from core.questionnaire.loader import load_questions
from core.questionnaire.memory import MemoryMainAnswerStore


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
    assert message("feature_stub", "streamlit") in unlocked.text


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
