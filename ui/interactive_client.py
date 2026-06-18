# coding: utf-8
"""
Общая логика текстовых клиентов (console, telegram).

Цель:
    Не дублировать обработку ответов AppService между консолью и Telegram.
    График страны: Telegram и Streamlit; в консоли — только текст.

Выход:
    Обновлённый state после шага сценария; для FIND_COUNTRY — дополненный текст профиля.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.country_profiles import format_country_profile
from core.messages import back_to_menu_button, button, message
from core.models import (
    ACTION_BACK_TO_MENU,
    ACTION_MAIN_ANSWER,
    ACTION_MAIN_RETURN_LATER,
    ACTION_NAME_ENTERED,
    ACTION_SECONDARY_ANSWER,
    ACTION_SECONDARY_RETURN_LATER,
    AppResponse,
    Screen,
    UserIdentity,
)
from ui.helpers import apply_response, build_payload, with_screen_context


def registered_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Поля зарегистрированного пользователя для payload AppService."""
    return build_payload(
        user_name=state.get("user_name"),
        registration_date=state.get("registration_date"),
    )


def sync_profile_from_db(service, identity: UserIdentity, state: dict[str, Any]) -> None:
    """Подтянуть user_name и registration_date из логгера в session state."""
    profile = service.logger.get_user_profile(identity)
    if not profile:
        return

    user_name = str(profile.get("user_name") or "").strip()
    if user_name:
        state["user_name"] = user_name

    reg_date = profile.get("registration_date")
    if reg_date is not None:
        if isinstance(reg_date, datetime):
            state["registration_date"] = reg_date.isoformat()
        else:
            state["registration_date"] = str(reg_date)


def enrich_find_country_console(
    service,
    state: dict[str, Any],
    identity: UserIdentity,
    channel: str,
    config: dict[str, Any],
) -> None:
    """Консоль: только текстовая карточка страны (без графика)."""
    if channel != "console":
        return
    screen = state.get("screen", "")
    if screen != Screen.FIND_COUNTRY.value:
        state.pop("country_profile_appended", None)
        return

    meta = state.get("meta", {})
    if not meta.get("show_country_plot") or state.get("country_profile_appended"):
        return

    country_code = str(meta.get("country_code", ""))
    profile_text = format_country_profile(country_code, channel)
    if profile_text.strip():
        state["last_text"] = f"{state.get('last_text', '')}\n\n{profile_text}"
    state["country_profile_appended"] = True


def handle_name_entered(
    service,
    identity: UserIdentity,
    channel: str,
    state: dict[str, Any],
    user_name: str,
) -> AppResponse:
    """Шаг ввода имени на экране START."""
    response = service.handle_action(
        identity,
        channel,
        ACTION_NAME_ENTERED,
        build_payload(text=user_name),
    )
    reg_name = None
    reg_date = None
    if response.screen == Screen.MAIN_MENU:
        reg_name = user_name.strip()
        reg_date = datetime.now().isoformat()
    apply_response(state, response, user_name=reg_name, registration_date=reg_date)
    return response


def handle_raw_input(
    service,
    identity: UserIdentity,
    channel: str,
    state: dict[str, Any],
    text: str,
    *,
    config: dict[str, Any] | None = None,
) -> AppResponse:
    """Произвольный ввод: меню, аналитика, «В главное меню»."""
    screen = state.get("screen", Screen.START.value)
    if text == back_to_menu_button(channel):
        response = service.handle_action(
            identity,
            channel,
            ACTION_BACK_TO_MENU,
            {
                **registered_payload(state),
                **build_payload(screen=screen),
            },
        )
    else:
        response = service.handle_action(
            identity,
            channel,
            "raw",
            with_screen_context(
                state,
                {
                    **registered_payload(state),
                    **build_payload(text=text, screen=screen),
                },
            ),
        )
    apply_response(state, response)
    if config is not None:
        enrich_find_country_console(service, state, identity, channel, config)
    state["main_questionary_complete"] = service.is_main_questionary_complete(identity)
    return response


def submit_questionnaire_answer(
    service,
    identity: UserIdentity,
    channel: str,
    state: dict[str, Any],
    *,
    screen: str,
    answer_action: str,
    answer: str,
    selected: str,
) -> AppResponse:
    """Отправить ответ на вопрос основной или дополнительной анкеты."""
    response = service.handle_action(
        identity,
        channel,
        answer_action,
        {
            **registered_payload(state),
            **build_payload(screen=screen),
            "answer": answer,
            "selected": selected,
        },
    )
    apply_response(state, response)
    state["main_questionary_complete"] = service.is_main_questionary_complete(identity)
    return response


def return_later_from_questionnaire(
    service,
    identity: UserIdentity,
    channel: str,
    state: dict[str, Any],
    *,
    screen: str,
    return_action: str,
) -> AppResponse:
    """Прервать анкету и вернуться в главное меню."""
    response = service.handle_action(
        identity,
        channel,
        return_action,
        registered_payload(state),
    )
    apply_response(state, response)
    return response


def questionnaire_choice_buttons(state: dict[str, Any], channel: str) -> list[str]:
    """Кнопки вариантов ответа без «Вернуться позже»."""
    meta = state.get("meta", {})
    return_later_label = meta.get("return_later_label", button("return_later", channel))
    return [label for label in state.get("buttons", []) if label != return_later_label]


def is_questionnaire_screen(screen: str) -> bool:
    return screen in (
        Screen.MAIN_QUESTIONARY.value,
        Screen.SECONDARY_QUESTIONARY.value,
    )


def questionnaire_actions(screen: str) -> tuple[str, str]:
    """(answer_action, return_action) для экрана анкеты."""
    if screen == Screen.MAIN_QUESTIONARY.value:
        return ACTION_MAIN_ANSWER, ACTION_MAIN_RETURN_LATER
    return ACTION_SECONDARY_ANSWER, ACTION_SECONDARY_RETURN_LATER


def console_plot_note(channel: str) -> str:
    """Подсказка в консоли, что график доступен в Streamlit/Telegram."""
    if channel == "console":
        return message("console_plot_skipped", channel)
    return ""
