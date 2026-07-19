from __future__ import annotations

from datetime import datetime

from core.app import AppService
from core.brain import greeting_display_name, resolve_telegram_user_name
from core.logging.noop import NoopLogger
from core.models import ACTION_NAME_CONFIRMED, Screen
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


def test_handle_start_new_telegram_user_goes_to_confirm_without_registration() -> None:
    service = _service()
    identity = service.logger.ensure_user("telegram", "249792088")

    class RecordingLogger(NoopLogger):
        def __init__(self, inner: NoopLogger) -> None:
            super().__init__()
            self.inner = inner
            self.events: list[str] = []

        def ensure_user(self, channel: str, external_user_id: str):
            return self.inner.ensure_user(channel, external_user_id)

        def get_user_profile(self, identity):
            return self.inner.get_user_profile(identity)

        def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
            self.events.append(event_name)

    recording = RecordingLogger(service.logger)
    service.logger = recording

    response = service.handle_start(
        identity,
        "telegram",
        {"telegram_username": "rosolimo"},
    )

    assert response.screen == Screen.NAME_CONFIRM
    assert "registration" not in recording.events


def test_handle_name_confirmed_logs_registration() -> None:
    service = _service()
    identity = service.logger.ensure_user("telegram", "249792099")

    class RecordingLogger(NoopLogger):
        def __init__(self, inner: NoopLogger) -> None:
            super().__init__()
            self.inner = inner
            self.events: list[str] = []

        def ensure_user(self, channel: str, external_user_id: str):
            return self.inner.ensure_user(channel, external_user_id)

        def upsert_user(self, *args, **kwargs):
            return self.inner.upsert_user(*args, **kwargs)

        def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
            self.events.append(event_name)

    recording = RecordingLogger(service.logger)
    service.logger = recording

    service.handle_action(
        identity,
        "telegram",
        ACTION_NAME_CONFIRMED,
        {
            "user_name": "rosolimo",
            "registration_source": "telegram_username",
        },
    )

    assert "registration" in recording.events


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
