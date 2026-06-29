from __future__ import annotations

from datetime import datetime

from core.app import AppService
from core.brain import greeting_display_name, resolve_telegram_user_name
from core.logging.noop import NoopLogger
from core.models import Screen
from core.questionnaire.loader import load_questions
from core.questionnaire.memory import MemoryMainAnswerStore, MemorySecondaryAnswerStore


def _service() -> AppService:
    return AppService(
        NoopLogger(),
        {
            "app": {"interface": "telegram", "logging_enabled": False},
            "logging": {"schema": "wvs"},
            "telegram": {"token": "test"},
            "paths": {"questions_file": "questions.json"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
        questions_data=load_questions("questions.json"),
    )


def test_resolve_telegram_user_name_replaces_numeric_id() -> None:
    assert (
        resolve_telegram_user_name(
            "249792088",
            external_user_id="249792088",
            telegram_username="rosolimo",
        )
        == "rosolimo"
    )


def test_greeting_display_name_adds_at_for_telegram_username() -> None:
    assert (
        greeting_display_name(
            "rosolimo",
            "telegram",
            telegram_username="rosolimo",
        )
        == "@rosolimo"
    )


def test_greeting_display_name_keeps_custom_name_without_at() -> None:
    assert greeting_display_name("Роман", "telegram", telegram_username="rosolimo") == "Роман"


def test_handle_start_returning_telegram_user_fixes_stored_id() -> None:
    service = _service()
    identity = service.logger.ensure_user("telegram", "249792088")
    service.logger.upsert_user(
        identity=identity,
        user_name="249792088",
        registration_date=datetime.now(),
        registration_channel="telegram",
        last_active_at=datetime.now(),
    )

    response = service.handle_start(
        identity,
        "telegram",
        {"telegram_username": "rosolimo"},
    )

    assert response.screen == Screen.MAIN_MENU
    assert "@rosolimo" in response.text
    profile = service.logger.get_user_profile(identity)
    assert profile is not None
    assert profile["user_name"] == "rosolimo"
