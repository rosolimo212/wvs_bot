# coding: utf-8
"""
AppService — оркестратор ядра WVS.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.analytics.indices import compute_main_indices
from core.analytics.country import find_nearest_country
from core.analytics.position import find_age_position, find_gender_age_position, find_global_position
from core.learn_more import learn_more_question_title
from core.brain import (
    is_back_to_learn_more,
    is_back_to_menu,
    is_return_later,
    match_learn_more_question,
    match_menu_button,
    on_change_name_prompt,
    on_empty_name,
    on_feature_locked,
    on_find_country,
    on_find_own_place,
    on_analytics_no_data,
    on_learn_more_answer_reminder,
    on_learn_more_hub,
    on_learn_more_reminder,
    on_learn_more_answer,
    on_main_answer_empty,
    on_main_answer_invalid,
    on_main_menu_reminder,
    on_main_question_show,
    on_main_questionary_complete,
    on_name_entered,
    on_secondary_question_show,
    on_secondary_questionary_complete,
    on_start,
    on_telegram_name_confirm,
)
from core.messages import change_name_button, confirm_name_button, message
from core.questionnaire.loader import question_input_mode
from core.logging.base import EventLogger
from core.models import (
    ACTION_BACK_TO_MENU,
    ACTION_MAIN_ANSWER,
    ACTION_MAIN_RETURN_LATER,
    ACTION_NAME_CHANGE,
    ACTION_NAME_CONFIRMED,
    ACTION_NAME_ENTERED,
    ACTION_LEARN_MORE,
    ACTION_LEARN_MORE_BACK,
    ACTION_OPTION_1,
    ACTION_OPTION_2,
    ACTION_OPTION_3,
    ACTION_OPTION_4,
    ACTION_SECONDARY_ANSWER,
    ACTION_SECONDARY_RETURN_LATER,
    AppResponse,
    Screen,
    UserIdentity,
)
from core.questionnaire.base import MainAnswerStore
from core.questionnaire.loader import get_main_questions, get_secondary_questions, load_questions


class AppService:
    """Единая точка входа бизнес-логики для всех интерфейсов."""

    def __init__(
        self,
        logger: EventLogger,
        config: dict[str, Any],
        *,
        answer_store: MainAnswerStore | None = None,
        secondary_answer_store: MainAnswerStore | None = None,
        questions_data: dict[str, Any] | None = None,
    ) -> None:
        self.logger = logger
        self.config = config
        self._answer_store = answer_store
        self._secondary_answer_store = secondary_answer_store
        self._questions_data = questions_data or self._load_questions_data()
        self._main_questions = get_main_questions(self._questions_data)
        self._secondary_questions = get_secondary_questions(self._questions_data)

    def _load_questions_data(self) -> dict[str, Any]:
        questions_path = self.config.get("paths", {}).get("questions_file", "questions.json")
        root = Path(__file__).resolve().parents[1]
        return load_questions(root / questions_path)

    @property
    def answer_store(self) -> MainAnswerStore:
        if self._answer_store is None:
            raise RuntimeError("MainAnswerStore не инициализирован")
        return self._answer_store

    @property
    def secondary_answer_store(self) -> MainAnswerStore:
        if self._secondary_answer_store is None:
            raise RuntimeError("SecondaryAnswerStore не инициализирован")
        return self._secondary_answer_store

    def is_main_questionary_complete(self, identity: UserIdentity) -> bool:
        return self.answer_store.is_complete(identity.user_id, len(self._main_questions))

    def is_secondary_questionary_complete(self, identity: UserIdentity) -> bool:
        return self.secondary_answer_store.is_complete(
            identity.user_id,
            len(self._secondary_questions),
        )

    def _resolve_identity(
        self, identity: UserIdentity, channel: str
    ) -> UserIdentity:
        return self.logger.ensure_user(channel, identity.external_user_id)

    def _screen_from_payload(self, payload: dict[str, Any]) -> str:
        screen = payload.get("screen")
        if isinstance(screen, Screen):
            return screen.value
        if screen:
            return str(screen)
        return Screen.MAIN_MENU.value

    def _log_main_menu_visit(self, identity: UserIdentity, channel: str) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="main_menu_visit",
            channel=channel,
            event_parameters=None,
        )

    def _log_faq_menu_visit(self, identity: UserIdentity, channel: str) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="faq_menu_visit",
            channel=channel,
            event_parameters=None,
        )

    def _log_faq_page_visit(
        self,
        identity: UserIdentity,
        channel: str,
        *,
        screen_name: str,
    ) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="faq_page_visit",
            channel=channel,
            event_parameters={"screen_name": screen_name},
        )

    def _log_main_menu_click(
        self,
        identity: UserIdentity,
        channel: str,
        *,
        from_screen: str,
    ) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="main_menu_click",
            channel=channel,
            event_parameters={"screen": from_screen},
        )

    def _log_find_country_start(
        self,
        identity: UserIdentity,
        channel: str,
        *,
        answer: str,
    ) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="find_counry_start",
            channel=channel,
            event_parameters={"answer": answer},
        )

    def _log_find_own_place_start(
        self,
        identity: UserIdentity,
        channel: str,
        *,
        answer: str,
    ) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="find_own_place_start",
            channel=channel,
            event_parameters={"answer": answer},
        )

    def log_country_plot_loaded(
        self,
        identity: UserIdentity,
        channel: str,
        *,
        sql_ms: int,
        processing_ms: int,
        render_ms: int,
        country_plot_loaded_ms: int,
        total_ms: int,
    ) -> None:
        self.logger.log_event(
            identity=identity,
            event_name="country_plot_loaded",
            channel=channel,
            event_parameters={
                "sql_ms": sql_ms,
                "processing_ms": processing_ms,
                "render_ms": render_ms,
                "country_plot_loaded_ms": country_plot_loaded_ms,
                "total_ms": total_ms,
            },
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

        if action == ACTION_LEARN_MORE:
            return self._handle_learn_more(identity, channel, payload)

        if action == ACTION_LEARN_MORE_BACK:
            return self._handle_learn_more_back(identity, channel, payload)

        if action == ACTION_OPTION_1:
            return self._handle_option_1(identity, channel, payload)

        if action == ACTION_OPTION_2:
            return self._handle_option_2(identity, channel, payload)

        if action == ACTION_OPTION_3:
            return self._handle_option_3(identity, channel, payload)

        if action == ACTION_OPTION_4:
            return self._handle_option_4(identity, channel, payload)

        if action == ACTION_MAIN_ANSWER:
            return self._handle_main_answer(identity, channel, payload)

        if action == ACTION_MAIN_RETURN_LATER:
            return self._handle_main_return_later(identity, channel, payload)

        if action == ACTION_SECONDARY_ANSWER:
            return self._handle_secondary_answer(identity, channel, payload)

        if action == ACTION_SECONDARY_RETURN_LATER:
            return self._handle_secondary_return_later(identity, channel, payload)

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

        if screen == Screen.SECONDARY_QUESTIONARY.value or screen == Screen.SECONDARY_QUESTIONARY:
            if is_return_later(raw_text, channel):
                return self._handle_secondary_return_later(identity, channel, payload)

        if screen == Screen.LEARN_MORE.value or screen == Screen.LEARN_MORE:
            if is_back_to_menu(raw_text, channel):
                return self._handle_back_to_menu(identity, channel, payload)
            item = match_learn_more_question(raw_text, channel)
            if item is not None:
                return self._handle_learn_more_item(identity, channel, payload, item)
            self._touch_user(identity, channel, payload)
            return on_learn_more_reminder(channel)

        if screen == Screen.LEARN_MORE_ANSWER.value or screen == Screen.LEARN_MORE_ANSWER:
            if is_back_to_learn_more(raw_text, channel):
                return self._handle_learn_more_back(identity, channel, payload)
            if is_back_to_menu(raw_text, channel):
                return self._handle_back_to_menu(identity, channel, payload)
            item = int(payload.get("learn_more_item") or 0)
            if item:
                self._touch_user(identity, channel, payload)
                return on_learn_more_answer_reminder(item, channel)
            return on_learn_more_reminder(channel)

        if is_back_to_menu(raw_text, channel):
            return self._handle_back_to_menu(identity, channel, payload)

        matched = match_menu_button(raw_text, channel)
        if matched == "learn_more":
            return self._handle_learn_more(identity, channel, payload)
        if matched == "option_1":
            return self._handle_option_1(identity, channel, payload)
        if matched == "option_2":
            return self._handle_option_2(identity, channel, payload)
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
        return on_name_entered(
            user_name,
            channel,
            is_registration=True,
            **self._menu_meta(identity),
        )

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
        return on_name_entered(
            user_name,
            channel,
            is_registration=True,
            **self._menu_meta(identity),
        )

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

    def _handle_learn_more(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self._log_faq_menu_visit(identity, channel)
        return on_learn_more_hub(channel)

    def _handle_learn_more_back(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self._log_faq_menu_visit(identity, channel)
        return on_learn_more_hub(channel)

    def _handle_learn_more_item(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
        item: int,
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        self._log_faq_page_visit(
            identity,
            channel,
            screen_name=learn_more_question_title(item, channel),
        )
        return on_learn_more_answer(item, channel)

    def _handle_option_1(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        return self._show_main_question(identity, channel, payload)

    def _handle_option_2(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        return self._show_secondary_question(identity, channel, payload, show_intro=True)

    def _logging_config(self) -> dict[str, Any] | None:
        if self.config.get("app", {}).get("logging_enabled"):
            return self.config.get("logging")
        return None

    def _reference_schema(self) -> str:
        analytics_schema = self.config.get("analytics", {}).get("reference_schema")
        if analytics_schema:
            return str(analytics_schema)
        logging_cfg = self.config.get("logging") or {}
        return str(logging_cfg.get("schema", "wvs"))

    def _handle_option_3(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        if not self.is_main_questionary_complete(identity):
            response = on_feature_locked(channel, **self._menu_meta(identity))
            self._log_find_country_start(identity, channel, answer=response.text)
            return response

        logging_config = self._logging_config()
        if logging_config is None:
            response = on_analytics_no_data(channel, screen=Screen.FIND_COUNTRY)
            self._log_find_country_start(identity, channel, answer=response.text)
            return response

        try:
            result = find_nearest_country(
                identity.user_id,
                logging_config,
                reference_schema=self._reference_schema(),
            )
        except Exception:
            result = None
        if result is None:
            response = on_analytics_no_data(channel, screen=Screen.FIND_COUNTRY)
            self._log_find_country_start(identity, channel, answer=response.text)
            return response

        response = on_find_country(
            rv=result.rv,
            sv=result.sv,
            country_code=result.country_code,
            country_rv=result.country_rv,
            country_sv=result.country_sv,
            channel=channel,
        )
        self._log_find_country_start(identity, channel, answer=response.text)
        return response

    def _handle_option_4(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        if not self.is_main_questionary_complete(identity):
            response = on_feature_locked(channel, **self._menu_meta(identity))
            self._log_find_own_place_start(identity, channel, answer=response.text)
            return response

        logging_config = self._logging_config()
        if logging_config is None:
            response = on_analytics_no_data(channel, screen=Screen.FIND_OWN_PLACE)
            self._log_find_own_place_start(identity, channel, answer=response.text)
            return response

        try:
            global_pos = find_global_position(
                identity.user_id,
                logging_config,
                reference_schema=self._reference_schema(),
            )
        except Exception:
            global_pos = None
        if global_pos is None:
            response = on_analytics_no_data(channel, screen=Screen.FIND_OWN_PLACE)
            self._log_find_own_place_start(identity, channel, answer=response.text)
            return response

        parts = [
            message(
                "find_own_place_global",
                channel,
                rv=global_pos.rv,
                sv=global_pos.sv,
                rv_rank=global_pos.rv_rank,
                sv_rank=global_pos.sv_rank,
            )
        ]

        try:
            age_pos = find_age_position(
                identity.user_id,
                logging_config,
                reference_schema=self._reference_schema(),
            )
        except Exception:
            age_pos = None
        if age_pos:
            parts.append(
                message(
                    "find_own_place_age",
                    channel,
                    rv_rank=age_pos.rv_rank,
                    sv_rank=age_pos.sv_rank,
                )
            )

        try:
            gender_age_pos = find_gender_age_position(
                identity.user_id,
                logging_config,
                reference_schema=self._reference_schema(),
            )
        except Exception:
            gender_age_pos = None
        if gender_age_pos:
            parts.append(
                message(
                    "find_own_place_gender_age",
                    channel,
                    rv_rank=gender_age_pos.rv_rank,
                    sv_rank=gender_age_pos.sv_rank,
                )
            )
        elif age_pos is None:
            parts.append(message("find_own_place_secondary_hint", channel))

        result_text = "\n\n".join(parts)
        self._log_find_own_place_start(identity, channel, answer=result_text)
        return on_find_own_place(result_text, channel)

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
        if next_index == 0:
            self.logger.log_event(
                identity=identity,
                event_name="main_questionary_start",
                channel=channel,
                event_parameters=None,
            )
        self.logger.log_event(
            identity=identity,
            event_name="question_show",
            channel=channel,
            event_parameters={
                "questionary": "main",
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
        input_mode = question_input_mode(question)

        if input_mode == "text":
            if selected in question["variants"]:
                final_answer = selected
            elif answer:
                final_answer = answer
            else:
                response = on_main_answer_empty(channel)
                return self._restore_current_question(response, question, next_index, total, channel)
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
                "questionary": "main",
                "qv_number": int(question["num"]),
                "qv_id": question["id"],
                "qv_text": question["text"],
                "answer": final_answer,
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
        self._log_main_menu_visit(identity, channel)
        logging_config = self.config.get("logging") if self.config.get("app", {}).get("logging_enabled") else None
        indices = compute_main_indices(
            self.answer_store,
            identity.user_id,
            logging_config=logging_config,
        )
        if indices is None:
            rv, sv = 0, 0
        else:
            rv, sv = indices
        return on_main_questionary_complete(rv=rv, sv=sv, channel=channel)

    def _show_secondary_question(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
        *,
        show_intro: bool = False,
    ) -> AppResponse:
        total = len(self._secondary_questions)
        next_index = self.secondary_answer_store.get_next_question_index(identity.user_id, total)
        if next_index is None:
            return self._complete_secondary_questionary(identity, channel, payload)

        question = self._secondary_questions[next_index]
        remaining = total - next_index
        if next_index == 0:
            self.logger.log_event(
                identity=identity,
                event_name="secondary_questionary_start",
                channel=channel,
                event_parameters=None,
            )
        self.logger.log_event(
            identity=identity,
            event_name="question_show",
            channel=channel,
            event_parameters={
                "questionary": "secondary",
                "qv_number": int(question["num"]),
                "qv_id": question["id"],
            },
        )
        return on_secondary_question_show(
            question,
            remaining=remaining,
            channel=channel,
            show_intro=show_intro,
        )

    def _handle_secondary_answer(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        identity = self._resolve_identity(identity, channel)
        self._touch_user(identity, channel, payload)

        total = len(self._secondary_questions)
        next_index = self.secondary_answer_store.get_next_question_index(identity.user_id, total)
        if next_index is None:
            return self._complete_secondary_questionary(identity, channel, payload)

        question = self._secondary_questions[next_index]
        selected = str(payload.get("selected", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        input_mode = question_input_mode(question)

        if input_mode == "text":
            if selected in question["variants"]:
                final_answer = selected
            elif answer:
                final_answer = answer
            else:
                response = on_main_answer_empty(channel)
                return self._restore_secondary_question(response, question, next_index, total, channel)
        elif selected in question["variants"]:
            final_answer = selected
        else:
            response = on_main_answer_invalid(channel)
            return self._restore_secondary_question(response, question, next_index, total, channel)

        user_name = str(payload.get("user_name", "")).strip() or identity.user_id
        self.secondary_answer_store.save_answer(identity.user_id, user_name, question, final_answer)
        self.logger.log_event(
            identity=identity,
            event_name="answer_sent",
            channel=channel,
            event_parameters={
                "questionary": "secondary",
                "qv_number": int(question["num"]),
                "qv_id": question["id"],
                "qv_text": question["text"],
                "answer": final_answer,
            },
        )
        return self._show_secondary_question(identity, channel, payload)

    def _restore_secondary_question(
        self,
        response: AppResponse,
        question: dict[str, Any],
        next_index: int,
        total: int,
        channel: str,
    ) -> AppResponse:
        question_response = on_secondary_question_show(
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

    def _complete_secondary_questionary(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        self._log_main_menu_visit(identity, channel)
        return on_secondary_questionary_complete(channel)

    def _handle_secondary_return_later(
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
        from_screen = self._screen_from_payload(payload)
        self._log_main_menu_click(identity, channel, from_screen=from_screen)
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
