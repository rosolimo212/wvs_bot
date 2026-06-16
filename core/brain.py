# coding: utf-8
"""
Мозг системы — чистая логика сценария без I/O.

Цель:
    Определить переходы экранов и тексты ответов для WVS-бота.

Вход:
    Действия пользователя (имя, выбор пункта меню).

Выход:
    AppResponse — единый ответ ядра для любого UI-клиента.
"""

from __future__ import annotations

from core.messages import (
    BACK_TO_MENU_BUTTON,
    CHANGE_NAME_BUTTON,
    CONFIRM_NAME_BUTTON,
    MENU_BUTTONS,
    back_to_menu_button,
    change_name_button,
    confirm_name_button,
    menu_buttons,
    message,
)
from core.models import AppResponse, Screen


def format_display_name(user_name: str, *, with_at: bool = False) -> str:
    clean = user_name.strip().lstrip("@")
    if not clean:
        return user_name
    if with_at:
        return f"@{clean}"
    return clean


def on_start(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("start_ask_name", channel),
        buttons=[],
        screen=Screen.START,
    )


def on_empty_name(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("empty_name", channel),
        buttons=[],
        screen=Screen.START,
    )


def on_name_entered(user_name: str, channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("main_menu_greeting", channel, user_name=user_name),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
    )


def on_telegram_name_confirm(user_name: str, channel: str | None = None) -> AppResponse:
    display = format_display_name(user_name, with_at=True)
    return AppResponse(
        text=message("telegram_name_confirm", channel, display=display),
        buttons=[
            confirm_name_button(channel),
            change_name_button(channel),
        ],
        screen=Screen.NAME_CONFIRM,
    )


def on_change_name_prompt(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("change_name_prompt", channel),
        buttons=[],
        screen=Screen.START,
    )


def on_main_menu_reminder(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("main_menu_reminder", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
    )


def on_main_questionary_stub(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("main_questionary_stub", channel),
        buttons=[back_to_menu_button(channel)],
        screen=Screen.MAIN_QUESTIONARY,
    )


def on_secondary_questionary_stub(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("secondary_questionary_stub", channel),
        buttons=[back_to_menu_button(channel)],
        screen=Screen.SECONDARY_QUESTIONARY,
    )


def on_find_country_locked(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("find_country_locked", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
    )


def on_find_own_place_locked(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("find_own_place_locked", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
    )


def match_menu_button(text: str, channel: str | None = None) -> str | None:
    normalized = text.strip().casefold()
    buttons = menu_buttons(channel)
    mapping = {
        buttons[0].casefold(): "option_1",
        buttons[1].casefold(): "option_2",
        buttons[2].casefold(): "option_3",
        buttons[3].casefold(): "option_4",
    }
    return mapping.get(normalized)


def is_back_to_menu(text: str, channel: str | None = None) -> bool:
    return text.strip().casefold() == back_to_menu_button(channel).casefold()


__all__ = [
    "BACK_TO_MENU_BUTTON",
    "CHANGE_NAME_BUTTON",
    "CONFIRM_NAME_BUTTON",
    "MENU_BUTTONS",
    "format_display_name",
    "is_back_to_menu",
    "match_menu_button",
    "on_change_name_prompt",
    "on_empty_name",
    "on_find_country_locked",
    "on_find_own_place_locked",
    "on_main_menu_reminder",
    "on_main_questionary_stub",
    "on_name_entered",
    "on_secondary_questionary_stub",
    "on_start",
    "on_telegram_name_confirm",
]
