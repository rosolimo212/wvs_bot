# coding: utf-8
"""
Мозг системы — чистая логика сценария без I/O.
"""

from __future__ import annotations

import math
from typing import Any

from core.messages import (
    BACK_TO_MENU_BUTTON,
    CHANGE_NAME_BUTTON,
    CONFIRM_NAME_BUTTON,
    MENU_BUTTONS,
    back_to_menu_button,
    change_name_button,
    confirm_name_button,
    custom_answer_button,
    menu_buttons,
    message,
    return_later_button,
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


def on_name_entered(
    user_name: str,
    channel: str | None = None,
    *,
    main_questionary_complete: bool = False,
) -> AppResponse:
    return AppResponse(
        text=message("main_menu_greeting", channel, user_name=user_name),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": main_questionary_complete},
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


def on_main_menu_reminder(
    channel: str | None = None,
    *,
    main_questionary_complete: bool = False,
) -> AppResponse:
    return AppResponse(
        text=message("main_menu_reminder", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": main_questionary_complete},
    )


def on_feature_stub(channel: str | None = None, *, screen: Screen) -> AppResponse:
    return AppResponse(
        text=message("feature_stub", channel),
        buttons=[back_to_menu_button(channel)],
        screen=screen,
    )


def on_feature_locked(
    channel: str | None = None,
    *,
    main_questionary_complete: bool = False,
) -> AppResponse:
    return AppResponse(
        text=message("feature_locked", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": main_questionary_complete},
    )


def estimate_minutes(remaining_questions: int) -> int:
    return int(math.floor(remaining_questions * 0.35))


def on_main_question_show(
    question: dict[str, Any],
    *,
    remaining: int,
    channel: str | None = None,
) -> AppResponse:
    time_est = estimate_minutes(remaining)
    custom_label = custom_answer_button(channel)
    return_later_label = return_later_button(channel)
    return AppResponse(
        text=message(
            "main_question_prompt",
            channel,
            remaining=remaining,
            time=time_est,
            q_num=int(question["num"]),
            q_text=question["text"],
        ),
        buttons=list(question["variants"]) + [custom_label, return_later_label],
        screen=Screen.MAIN_QUESTIONARY,
        meta={
            "qv_number": int(question["num"]),
            "qv_id": question["id"],
            "custom_answer_label": custom_label,
            "return_later_label": return_later_label,
        },
    )


def on_main_questionary_complete(
    user_name: str,
    channel: str | None = None,
) -> AppResponse:
    return AppResponse(
        text=message("main_questionary_complete", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": True},
    )


def on_main_answer_empty(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("main_answer_empty", channel),
        buttons=[],
        screen=Screen.MAIN_QUESTIONARY,
    )


def on_main_answer_invalid(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("main_answer_invalid", channel),
        buttons=[],
        screen=Screen.MAIN_QUESTIONARY,
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


def is_return_later(text: str, channel: str | None = None) -> bool:
    return text.strip().casefold() == return_later_button(channel).casefold()


__all__ = [
    "BACK_TO_MENU_BUTTON",
    "CHANGE_NAME_BUTTON",
    "CONFIRM_NAME_BUTTON",
    "MENU_BUTTONS",
    "estimate_minutes",
    "format_display_name",
    "is_back_to_menu",
    "is_return_later",
    "match_menu_button",
    "on_change_name_prompt",
    "on_empty_name",
    "on_feature_locked",
    "on_feature_stub",
    "on_main_answer_empty",
    "on_main_answer_invalid",
    "on_main_menu_reminder",
    "on_main_question_show",
    "on_main_questionary_complete",
    "on_name_entered",
    "on_start",
    "on_telegram_name_confirm",
]
