# coding: utf-8
"""
AppService — оркестратор ядра WVS.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.brain import (
    is_back_to_menu,
    is_return_later,
    match_menu_button,
    on_change_name_prompt,
    on_empty_name,
    on_feature_locked,
    on_feature_stub,
    on_main_answer_empty,
    on_main_answer_invalid,
    on_main_menu_reminder,
    on_main_question_show,
    on_main_questionary_complete,
    on_name_entered,
    on_start,
    on_telegram_name_confirm,
)
from core.messages import back_to_menu_button, change_name_button, confirm_name_button, custom_answer_button
from core.logging.base import EventLogger
from core.models import (
    ACTION_BACK_TO_MENU,
    ACTION_MAIN_ANSWER,
    ACTION_MAIN_RETURN_LATER,
    ACTION_NAME_CHANGE,
    ACTION_NAME_CONFIRMED,
    ACTION_NAME_ENTERED,
    ACTION_OPTION_1,
    ACTION_OPTION_2,
    ACTION_OPTION_3,
    ACTION_OPTION_4,
    AppResponse,
    Screen,
    UserIdentity,
)
from core.questionnaire.base import MainAnswerStore
from core.questionnaire.loader import get_main_questions, load_questions

_OPTION_START_EVENTS: dict[str, tuple[str, Screen]] = {
    ACTION_OPTION_1: ("main_questionary_start", Screen.MAIN_QUESTIONARY),
    ACTION_OPTION_2: ("secondary_questionary_start", Screen.SECONDARY_QUESTIONARY),
    ACTION_OPTION_3: ("find_counry_start", Screen.FIND_COUNTRY),
    ACTION_OPTION_4: ("find_own_place_start", Screen.FIND_OWN_PLACE),
}


class AppService:
    """Единая точка входа бизнес-логики для всех интерфейсов."""

    def __init__(
        self,
        logger: EventLogger,
        config: dict[str, Any],
        *,
        answer_store: MainAnswerStore | None = None,
        questions_data: dict[str, Any] | None = None,
    ) -> None:
        self.logger = logger
        self.config = config
        self._answer_store = answer_store
        self._questions_data = questions_data or self._load_questions_data()
        self._main_questions = get_main_questions(self._questions_data)

    def _load_questions_data(self) -> dict[str, Any]:
        questions_path = self.config.get("paths", {}).get("questions_file", "questions.json")
        root = Path(__file__).resolve().parents[1]
        return load_questions(root / questions_path)

    @property
    def answer_store(self) -> MainAnswerStore:
        if self._answer_store is None:
            raise RuntimeError("MainAnswerStore не инициализирован")
        return self._answer_store

    def is_main_questionary_complete(self, identity: UserIdentity) -> bool:
        return self.answer_store.is_complete(identity.user_id, len(self._main_questions))

    def _resolve_identity(
        self, identity: UserIdentity, channel: str
    ) -> UserIdentity:
        return self.logger.ensure_user(channel, identity.external_user_id)

    def _log_main_menu_visit(self, identity: UserIdentity, channel: str) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="main_menu_visit",
            channel=channel,
            event_parameters=None,
        )

    def _log_main_menu_click(self, identity: UserIdentity, channel: str) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="main_menu_click",
            channel=channel,
            event_parameters={"button": back_to_menu_button(channel)},
        )

    def _menu_meta(self, identity: UserIdentity) -> dict[str, Any]:
        return {
            "main_questionary_complete": self.is_main_questionary_complete(identity),
        }

    def handle_start(
        self,
        identity: UserIdentity,
        channel: str,
        context: dict[str, Any] | None = None,
    ) -> AppResponse:
        context = context or {}
        identity = self._resolve_identity(identity, channel)
        menu_meta = self._menu_meta(identity)

        profile = self.logger.get_user_profile(identity)
        existing_name = (profile or {}).get("user_name", "").strip()
        if existing_name:
            self._touch_user(
                identity,
                channel,
                {
                    "user_name": existing_name,
                    "registration_date": (profile or {}).get("registration_date"),
                },
            )
            self.logger.log_event(
                identity=identity,
                event_name="start_screen_visit",
                channel=channel,
                event_parameters=None,
            )
            self._log_main_menu_visit(identity, channel)
            return on_name_entered(existing_name, channel, **menu_meta)

        self._ensure_user_stub(identity, channel)
        self.logger.log_event(
            identity=identity,
            event_name="start_screen_visit",
            channel=channel,
            event_parameters=None,
        )

        if channel == "telegram":
            telegram_username = str(context.get("telegram_username") or "").strip()
            if telegram_username:
                return self._register_with_name(
                    identity,
                    channel,
                    telegram_username.lstrip("@"),
                    registration_source="telegram_username",
                    confirm=True,
                )

        return on_start(channel)

    def _ensure_user_stub(self, identity: UserIdentity, channel: str) -> None:
        now = datetime.now()
        self.logger.upsert_user(
            identity=identity,
            user_name="",
            registration_date=now,
            registration_channel=channel,
            last_active_at=now,
        )

    def handle_action(
        self,
        identity: UserIdentity,
        channel: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> AppResponse:
        payload = payload or {}

        if action == ACTION_NAME_ENTERED:
            return self._handle_name_entered(identity, channel, payload)

        if action == ACTION_NAME_CONFIRMED:
            return self._handle_name_confirmed(identity, channel, payload)

        if action == ACTION_NAME_CHANGE:
            return on_change_name_prompt(channel)

        if action == ACTION_OPTION_1:
            return self._handle_option_1(identity, channel, payload)

        if action == ACTION_OPTION_2:
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_2)

        if action == ACTION_OPTION_3:
            return self._handle_option_3(identity, channel, payload)

        if action == ACTION_OPTION_4:
            return self._handle_option_4(identity, channel, payload)

        if action == ACTION_MAIN_ANSWER:
            return self._handle_main_answer(identity, channel, payload)

        if action == ACTION_MAIN_RETURN_LATER:
            return self._handle_main_return_later(identity, channel, payload)

        if action == ACTION_BACK_TO_MENU:
            return self._handle_back_to_menu(identity, channel, payload)

        raw_text = str(payload.get("text", "")).strip()
        if raw_text:
            return self._handle_raw_text(identity, channel, payload, raw_text)

        return on_main_menu_reminder(channel, **self._menu_meta(identity))

    def _handle_raw_text(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
        raw_text: str,
    ) -> AppResponse:
        screen = payload.get("screen")

        if screen == Screen.START.value or screen == Screen.START:
            payload_with_text = dict(payload)
            payload_with_text["text"] = raw_text
            return self._handle_name_entered(identity, channel, payload_with_text)

        if screen == Screen.NAME_CONFIRM.value or screen == Screen.NAME_CONFIRM:
            if raw_text == confirm_name_button(channel):
                return self._handle_name_confirmed(identity, channel, payload)
            if raw_text == change_name_button(channel):
                return on_change_name_prompt(channel)
            payload_with_text = dict(payload)
            payload_with_text["text"] = raw_text
            return self._handle_name_entered(identity, channel, payload_with_text)

        if screen == Screen.MAIN_QUESTIONARY.value or screen == Screen.MAIN_QUESTIONARY:
            if is_return_later(raw_text, channel):
                return self._handle_main_return_later(identity, channel, payload)

        if is_back_to_menu(raw_text, channel):
            return self._handle_back_to_menu(identity, channel, payload)

        matched = match_menu_button(raw_text, channel)
        if matched == "option_1":
            return self._handle_option_1(identity, channel, payload)
        if matched == "option_2":
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_2)
        if matched == "option_3":
            return self._handle_option_3(identity, channel, payload)
        if matched == "option_4":
            return self._handle_option_4(identity, channel, payload)

        self._touch_user(identity, channel, payload)
        return on_main_menu_reminder(channel, **self._menu_meta(identity))

    def _register_with_name(
        self,
        identity: UserIdentity,
        channel: str,
        user_name: str,
        *,
        registration_source: str,
        confirm: bool = False,
    ) -> AppResponse:
        identity = self._resolve_identity(identity, channel)
        now = datetime.now()
        self.logger.upsert_user(
            identity=identity,
            user_name=user_name,
            registration_date=now,
            registration_channel=channel,
            last_active_at=now,
        )
        self.logger.log_event(
            identity=identity,
            event_name="registration",
            channel=channel,
            event_parameters={
                "user_name": user_name,
                "source": registration_source,
            },
        )
        if confirm:
            return on_telegram_name_confirm(user_name, channel)
        self._log_main_menu_visit(identity, channel)
        return on_name_entered(user_name, channel, **self._menu_meta(identity))

    def _handle_name_confirmed(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        user_name = str(payload.get("user_name", "")).strip()
        if not user_name:
            return on_empty_name(channel)

        identity = self._resolve_identity(identity, channel)
        self._touch_user(identity, channel, payload)
        self._log_main_menu_visit(identity, channel)
        return on_name_entered(user_name, channel, **self._menu_meta(identity))

    def _handle_name_entered(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        user_name = str(payload.get("text", "")).strip()
        if not user_name:
            return on_empty_name(channel)

        identity = self._resolve_identity(identity, channel)
        return self._register_with_name(
            identity,
            channel,
            user_name,
            registration_source="user_input",
            confirm=False,
        )

    def _handle_option_1(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self.logger.log_event(
            identity=identity,
            event_name="main_questionary_start",
            channel=channel,
            event_parameters=None,
        )
        return self._show_main_question(identity, channel, payload)

    def _handle_menu_option(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
        action: str,
    ) -> AppResponse:
        start_event, screen = _OPTION_START_EVENTS[action]
        self._touch_user(identity, channel, payload)
        self.logger.log_event(
            identity=identity,
            event_name=start_event,
            channel=channel,
            event_parameters={"action": action},
        )
        return on_feature_stub(channel, screen=screen)

    def _handle_option_3(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self.logger.log_event(
            identity=identity,
            event_name="find_counry_start",
            channel=channel,
            event_parameters=None,
        )
        if not self.is_main_questionary_complete(identity):
            return on_feature_locked(channel, **self._menu_meta(identity))
        return on_feature_stub(channel, screen=Screen.FIND_COUNTRY)

    def _handle_option_4(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self.logger.log_event(
            identity=identity,
            event_name="find_own_place_start",
            channel=channel,
            event_parameters=None,
        )
        if not self.is_main_questionary_complete(identity):
            return on_feature_locked(channel, **self._menu_meta(identity))
        return on_feature_stub(channel, screen=Screen.FIND_OWN_PLACE)

    def _show_main_question(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        total = len(self._main_questions)
        next_index = self.answer_store.get_next_question_index(identity.user_id, total)
        if next_index is None:
            return self._complete_main_questionary(identity, channel, payload)

        question = self._main_questions[next_index]
        remaining = total - next_index
        self.logger.log_event(
            identity=identity,
            event_name="question_show",
            channel=channel,
            event_parameters={
                "qv_number": int(question["num"]),
                "qv_id": question["id"],
            },
        )
        return on_main_question_show(question, remaining=remaining, channel=channel)

    def _handle_main_answer(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        identity = self._resolve_identity(identity, channel)
        self._touch_user(identity, channel, payload)

        total = len(self._main_questions)
        next_index = self.answer_store.get_next_question_index(identity.user_id, total)
        if next_index is None:
            return self._complete_main_questionary(identity, channel, payload)

        question = self._main_questions[next_index]
        selected = str(payload.get("selected", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        custom_label = custom_answer_button(channel)

        if selected == custom_label:
            if not answer:
                response = on_main_answer_empty(channel)
                return self._restore_current_question(response, question, next_index, total, channel)
            final_answer = answer
        elif selected in question["variants"]:
            final_answer = selected
        else:
            response = on_main_answer_invalid(channel)
            return self._restore_current_question(response, question, next_index, total, channel)

        user_name = str(payload.get("user_name", "")).strip() or identity.user_id
        self.answer_store.save_answer(identity.user_id, user_name, question, final_answer)
        self.logger.log_event(
            identity=identity,
            event_name="answer_sent",
            channel=channel,
            event_parameters={
                "qv_number": int(question["num"]),
                "qv_id": question["id"],
            },
        )
        return self._show_main_question(identity, channel, payload)

    def _restore_current_question(
        self,
        response: AppResponse,
        question: dict[str, Any],
        next_index: int,
        total: int,
        channel: str,
    ) -> AppResponse:
        question_response = on_main_question_show(
            question,
            remaining=total - next_index,
            channel=channel,
        )
        return AppResponse(
            text=f"{response.text}\n\n{question_response.text}",
            buttons=question_response.buttons,
            screen=question_response.screen,
            meta=question_response.meta,
        )

    def _complete_main_questionary(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        user_name = str(payload.get("user_name", "")).strip()
        self._log_main_menu_visit(identity, channel)
        if user_name:
            return on_main_questionary_complete(user_name, channel)
        return on_main_questionary_complete("", channel)

    def _handle_main_return_later(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self._log_main_menu_visit(identity, channel)
        user_name = str(payload.get("user_name", "")).strip()
        if user_name:
            return on_name_entered(user_name, channel, **self._menu_meta(identity))
        return on_main_menu_reminder(channel, **self._menu_meta(identity))

    def _handle_back_to_menu(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self._log_main_menu_click(identity, channel)
        self._log_main_menu_visit(identity, channel)
        user_name = str(payload.get("user_name", "")).strip()
        if user_name:
            return on_name_entered(user_name, channel, **self._menu_meta(identity))
        return on_main_menu_reminder(channel, **self._menu_meta(identity))

    def _touch_user(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> None:
        user_name = payload.get("user_name")
        if not user_name:
            return

        registration_date = self._parse_registration_date(payload)
        now = datetime.now()

        self.logger.upsert_user(
            identity=identity,
            user_name=str(user_name),
            registration_date=registration_date,
            registration_channel=channel,
            last_active_at=now,
        )

    def _parse_registration_date(self, payload: dict[str, Any]) -> datetime:
        raw = payload.get("registration_date")
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str) and raw:
            return datetime.fromisoformat(raw)
        return datetime.now()
