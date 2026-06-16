# coding: utf-8
"""
AppService — оркестратор ядра WVS.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.brain import (
    is_back_to_menu,
    match_menu_button,
    on_change_name_prompt,
    on_empty_name,
    on_feature_stub,
    on_main_menu_reminder,
    on_name_entered,
    on_start,
    on_telegram_name_confirm,
)
from core.messages import back_to_menu_button, change_name_button, confirm_name_button
from core.logging.base import EventLogger
from core.models import (
    ACTION_BACK_TO_MENU,
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

_OPTION_START_EVENTS: dict[str, tuple[str, Screen]] = {
    ACTION_OPTION_1: ("main_questionary_start", Screen.MAIN_QUESTIONARY),
    ACTION_OPTION_2: ("secondary_questionary_start", Screen.SECONDARY_QUESTIONARY),
    ACTION_OPTION_3: ("find_counry_start", Screen.FIND_COUNTRY),
    ACTION_OPTION_4: ("find_own_place_start", Screen.FIND_OWN_PLACE),
}


class AppService:
    """Единая точка входа бизнес-логики для всех интерфейсов."""

    def __init__(self, logger: EventLogger, config: dict[str, Any]) -> None:
        self.logger = logger
        self.config = config

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

    def handle_start(
        self,
        identity: UserIdentity,
        channel: str,
        context: dict[str, Any] | None = None,
    ) -> AppResponse:
        context = context or {}
        identity = self._resolve_identity(identity, channel)

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
            return on_name_entered(existing_name, channel)

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
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_1)

        if action == ACTION_OPTION_2:
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_2)

        if action == ACTION_OPTION_3:
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_3)

        if action == ACTION_OPTION_4:
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_4)

        if action == ACTION_BACK_TO_MENU:
            return self._handle_back_to_menu(identity, channel, payload)

        raw_text = str(payload.get("text", "")).strip()
        if raw_text:
            return self._handle_raw_text(identity, channel, payload, raw_text)

        return on_main_menu_reminder(channel)

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

        if is_back_to_menu(raw_text, channel):
            return self._handle_back_to_menu(identity, channel, payload)

        matched = match_menu_button(raw_text, channel)
        if matched == "option_1":
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_1)
        if matched == "option_2":
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_2)
        if matched == "option_3":
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_3)
        if matched == "option_4":
            return self._handle_menu_option(identity, channel, payload, ACTION_OPTION_4)

        self._touch_user(identity, channel, payload)
        return on_main_menu_reminder(channel)

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
        return on_name_entered(user_name, channel)

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
        return on_name_entered(user_name, channel)

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
            return on_name_entered(user_name, channel)
        return on_main_menu_reminder(channel)

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
