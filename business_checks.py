# coding: utf-8
"""
Слой 2 тестирования — бизнес-проверки из task.md.

Цель:
    Проверки сценария, логирования, идентификаторов и латентности
    вне обычных unit-тестов pytest. Запускается из pre_commit_check.sh.

Выход:
    Печать OK по каждому пункту или AssertionError с описанием.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.analytics.country import NearestCountry
from core.analytics.position import UserPosition
from core.app import AppService
from core.brain import MENU_BUTTONS, match_menu_button
from core.identity import make_user_id
from core.logging.factory import build_logger
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button
from core.models import (
    ACTION_MAIN_ANSWER,
    ACTION_NAME_ENTERED,
    ACTION_OPTION_1,
    ACTION_OPTION_2,
    ACTION_OPTION_3,
    ACTION_OPTION_4,
    ACTION_SECONDARY_ANSWER,
    Screen,
    UserIdentity,
)
from core.questionnaire.loader import load_questions
from core.questionnaire.memory import MemoryMainAnswerStore, MemorySecondaryAnswerStore

REQUIRED_EVENTS = [
    "start_screen_visit",
    "registration",
    "main_menu_visit",
    "main_questionary_start",
    "question_show",
    "answer_sent",
    "secondary_questionary_start",
    "find_counry_start",
    "find_own_place_start",
    "main_menu_click",
]

MAX_LATENCY_SEC = 8.0


class MemoryLogger:
    """In-memory логгер для проверки событий и users без postgres."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.users: dict[str, dict[str, Any]] = {}
        self._by_external: dict[tuple[str, str], UserIdentity] = {}
        self._counter = 0

    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        key = (channel, external_user_id)
        if key in self._by_external:
            return self._by_external[key]

        user_id = make_user_id(channel, external_user_id)
        if user_id in self.users:
            identity = UserIdentity(
                user_id,
                self.users[user_id]["internal_user_id"],
                external_user_id,
            )
            self._by_external[key] = identity
            return identity

        self._counter += 1
        self.users[user_id] = {
            "internal_user_id": self._counter,
            "external_user_id": external_user_id,
        }
        identity = UserIdentity(user_id, self._counter, external_user_id)
        self._by_external[key] = identity
        return identity

    def upsert_user(
        self,
        identity: UserIdentity,
        user_name: str,
        registration_date: datetime,
        registration_channel: str,
        last_active_at: datetime,
        is_paid: bool = False,
        is_trial: bool = False,
        is_active: bool = True,
    ) -> None:
        self.users[identity.user_id] = {
            "internal_user_id": identity.internal_user_id,
            "external_user_id": identity.external_user_id,
            "user_name": user_name,
            "registration_date": registration_date,
            "registration_channel": registration_channel,
            "last_active_at": last_active_at,
            "is_paid": is_paid,
            "is_trial": is_trial,
            "is_active": is_active,
        }

    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        _ = timestamp
        self.events.append(
            {
                "user_id": identity.user_id,
                "internal_user_id": identity.internal_user_id,
                "external_user_id": identity.external_user_id,
                "event_name": event_name,
                "channel": channel,
                "event_parameters": event_parameters,
            }
        )

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        row = self.users.get(identity.user_id)
        if row is None:
            return None
        return {
            "user_name": str(row.get("user_name", "")),
            "registration_date": row.get("registration_date"),
        }


def _make_service(logger: MemoryLogger | None = None) -> tuple[AppService, MemoryLogger]:
    log = logger or MemoryLogger()
    questions = load_questions(str(ROOT / "questions.json"))
    config = {
        "app": {"interface": "streamlit", "logging_enabled": True},
        "logging": {"schema": "wvs"},
        "telegram": {"token": "test"},
        "paths": {"questions_file": "questions.json"},
        "analytics": {"reference_schema": "wvs"},
    }
    service = AppService(
        logger=log,
        config=config,
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
        questions_data=questions,
    )
    return service, log


def _user_payload(user_name: str, registration_date: datetime) -> dict[str, Any]:
    return {
        "user_name": user_name,
        "registration_date": registration_date.isoformat(),
    }


def _answer_all_main(service: AppService, identity: UserIdentity, channel: str, payload: dict) -> None:
    service.handle_action(identity, channel, ACTION_OPTION_1, payload)
    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            channel,
            ACTION_MAIN_ANSWER,
            {
                **payload,
                "selected": variant,
                "answer": variant,
            },
        )


def _answer_all_secondary(service: AppService, identity: UserIdentity, channel: str, payload: dict) -> None:
    service.handle_action(identity, channel, ACTION_OPTION_2, payload)
    for question in service._secondary_questions:
        if question["id"] == "S01":
            answer = "1990"
            selected = ""
        elif question["id"] == "S02":
            answer = "Россия"
            selected = answer
        elif question["id"] == "S03":
            answer = "Мужчина"
            selected = answer
        else:
            variant = question["variants"][0]
            answer = variant
            selected = variant
        service.handle_action(
            identity,
            channel,
            ACTION_SECONDARY_ANSWER,
            {
                **payload,
                "selected": selected,
                "answer": answer,
            },
        )


def _mock_own_place() -> "OwnPlaceResult":
    from core.analytics.position import OwnPlaceContext, OwnPlaceResult, UserPosition

    return OwnPlaceResult(
        global_pos=UserPosition(rv=10.0, sv=12.0, rv_rank=55, sv_rank=60),
        context=OwnPlaceContext(
            country_code="RUS",
            country_name="Россия",
            used_default_country=False,
            user_country_missing_in_sample=False,
            age_window=3,
            age_sample_size=100,
            age_sample_too_small=False,
        ),
        age_pos=UserPosition(rv=10.0, sv=12.0, rv_rank=50, sv_rank=52),
        gender_age_pos=None,
        bot=None,
    )


def _run_full_scenario(service: AppService, logger: MemoryLogger, channel: str) -> UserIdentity:
    identity = logger.ensure_user(channel, "biz-check-user-1")
    service.handle_start(identity, channel)
    service.handle_action(identity, channel, ACTION_NAME_ENTERED, {"text": "Тестовый Пользователь"})
    payload = _user_payload(
        "Тестовый Пользователь",
        logger.users[identity.user_id]["registration_date"],
    )

    _answer_all_main(service, identity, channel, payload)

    _answer_all_secondary(service, identity, channel, payload)

    nearest = NearestCountry(
        rv=10.0,
        sv=12.0,
        country_code="RUS",
        country_rv=9.5,
        country_sv=11.5,
    )

    with patch("core.app.find_nearest_country", return_value=nearest):
        service.handle_action(identity, channel, ACTION_OPTION_3, payload)
    with patch("core.app.compute_own_place", return_value=_mock_own_place()):
        service.handle_action(identity, channel, ACTION_OPTION_4, payload)

    service.handle_action(
        identity,
        channel,
        "raw",
        {
            **payload,
            "text": back_to_menu_button(channel),
            "screen": Screen.FIND_OWN_PLACE.value,
        },
    )
    return identity


def check_project_scaffold_exists() -> None:
    required = [
        "core/identity.py",
        "core/app.py",
        "ui/streamlit_app.py",
        "ui/console_app.py",
        "ui/telegram_bot.py",
        "business_checks.py",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        raise AssertionError("Не найдены файлы: " + ", ".join(missing))


def check_logger_factory_builds() -> None:
    build_logger({"app": {"logging_enabled": False}, "logging": {"schema": "wvs"}})


def check_all_menu_buttons_defined() -> None:
    for label in MENU_BUTTONS:
        if match_menu_button(label) is None:
            raise AssertionError(f"Кнопка не распознаётся: {label!r}")


def check_all_menu_buttons_clickable() -> None:
    service, logger = _make_service()
    identity = logger.ensure_user("streamlit", "btn-test")
    service.handle_start(identity, "streamlit")
    service.handle_action(identity, "streamlit", ACTION_NAME_ENTERED, {"text": "Юля"})
    payload = _user_payload("Юля", logger.users[identity.user_id]["registration_date"])
    _answer_all_main(service, identity, "streamlit", payload)

    nearest = NearestCountry(10.0, 12.0, "RUS", 9.5, 11.5)
    with patch("core.app.find_nearest_country", return_value=nearest):
        with patch("core.app.compute_own_place", return_value=_mock_own_place()):
            for label in MENU_BUTTONS:
                resp = service.handle_action(
                    identity,
                    "streamlit",
                    "raw",
                    {
                        **payload,
                        "text": label,
                        "screen": Screen.MAIN_MENU.value,
                    },
                )
                if not resp.text.strip():
                    raise AssertionError(f"Пустой ответ на кнопку: {label!r}")


def check_all_events_logged() -> None:
    service, logger = _make_service()
    _run_full_scenario(service, logger, "console")
    logged = {event["event_name"] for event in logger.events}
    missing = [name for name in REQUIRED_EVENTS if name not in logged]
    if missing:
        raise AssertionError(f"Не залогированы: {missing}")


def check_users_have_three_ids() -> None:
    service, logger = _make_service()
    identity = _run_full_scenario(service, logger, "telegram")
    row = logger.users[identity.user_id]
    if not row.get("external_user_id"):
        raise AssertionError("external_user_id не сохранён")
    if row["internal_user_id"] != identity.internal_user_id:
        raise AssertionError("internal_user_id не совпадает")


def check_users_overwritten() -> None:
    service, logger = _make_service()
    identity = logger.ensure_user("console", "overwrite-test")
    service.handle_action(identity, "console", ACTION_NAME_ENTERED, {"text": "Петр"})
    first_active = logger.users[identity.user_id]["last_active_at"]
    payload = _user_payload("Петр", logger.users[identity.user_id]["registration_date"])
    time.sleep(0.01)
    service.handle_action(identity, "console", ACTION_OPTION_2, payload)
    if logger.users[identity.user_id]["last_active_at"] < first_active:
        raise AssertionError("last_active_at не обновился")


def check_no_user_id_collisions() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        counter = Path(tmp) / "user_counter.json"
        logger = NoopLogger(counter_path=counter)
        internal_ids: list[int] = []
        for index in range(50):
            ident = logger.ensure_user("streamlit", f"session-{index}")
            internal_ids.append(ident.internal_user_id)
            if index > 0 and ident.user_id == make_user_id("streamlit", f"session-{index - 1}"):
                raise AssertionError("hash user_id коллизия")
        if len(internal_ids) != len(set(internal_ids)):
            raise AssertionError("Коллизии internal_user_id")


def check_special_chars_safe() -> None:
    name = 'O\'Brien "test" 🎉'
    service, logger = _make_service()
    identity = logger.ensure_user("telegram", "spec-1")
    service.handle_start(identity, "telegram")
    service.handle_action(identity, "telegram", ACTION_NAME_ENTERED, {"text": name})
    registration_events = [event for event in logger.events if event["event_name"] == "registration"]
    if not registration_events:
        raise AssertionError("registration не залогирован")
    if registration_events[0]["event_parameters"]["user_name"] != name:
        raise AssertionError("Имя исказилось в логе")


def check_scenario_latency_under_limit() -> None:
    service, logger = _make_service()
    started = time.monotonic()
    with patch("core.app.find_nearest_country") as mock_country:
        mock_country.return_value = NearestCountry(10.0, 12.0, "RUS", 9.5, 11.5)
        with patch("core.app.compute_own_place", return_value=_mock_own_place()):
            _run_full_scenario(service, logger, "streamlit")
    elapsed = time.monotonic() - started
    if elapsed >= MAX_LATENCY_SEC:
        raise AssertionError(f"Сценарий занял {elapsed:.2f} с")


def check_country_plot_timing_report() -> None:
    """Печать таймингов карты (как в pre_commit_check) для наглядности."""
    from scripts.country_plot_timing_check import main as timing_main

    timing_main()


def run_all_checks() -> None:
    checks = [
        ("каркас проекта", check_project_scaffold_exists),
        ("фабрика логгера", check_logger_factory_builds),
        ("кнопки меню определены", check_all_menu_buttons_defined),
        ("кнопки меню кликабельны", check_all_menu_buttons_clickable),
        ("все события логируются", check_all_events_logged),
        ("три id в users", check_users_have_three_ids),
        ("users перезаписываются", check_users_overwritten),
        ("нет коллизий user_id", check_no_user_id_collisions),
        ("спецсимволы безопасны", check_special_chars_safe),
        (f"латентность сценария < {MAX_LATENCY_SEC} с", check_scenario_latency_under_limit),
        ("тайминги карты стран", check_country_plot_timing_report),
    ]

    print("business_checks:")
    for title, fn in checks:
        fn()
        print(f"  OK: {title}")

    print("business_checks: OK")


if __name__ == "__main__":
    run_all_checks()
