# coding: utf-8
"""
Мозг системы — чистая логика сценария без I/O.
"""

from __future__ import annotations

import math
from typing import Any

from core.questionnaire.loader import question_input_mode

from core.analytics.index_interpretation import format_indices_summary
from core.learn_more import (
    is_back_to_learn_more,
    learn_more_answer_buttons,
    learn_more_answer_text,
    learn_more_hub_text,
    learn_more_question_buttons,
    learn_more_question_title,
    match_learn_more_question,
)
from core.messages import (
    BACK_TO_MENU_BUTTON,
    CHANGE_NAME_BUTTON,
    CONFIRM_NAME_BUTTON,
    MENU_BUTTONS,
    back_to_learn_more_button,
    back_to_menu_button,
    change_name_button,
    confirm_name_button,
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


def compose_start_screen_text(channel: str | None = None, *, ask_name: bool = True) -> str:
    """Вводный текст о боте и, при необходимости, приглашение представиться."""
    intro = message("start_intro", channel)
    if not ask_name:
        return intro
    return f"{intro}\n\n{message('start_ask_name', channel)}"


def on_start(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=compose_start_screen_text(channel),
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
    is_registration: bool = False,
) -> AppResponse:
    greeting = "main_menu_greeting_new" if is_registration else "main_menu_greeting_return"
    return AppResponse(
        text=message(greeting, channel, user_name=user_name),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": main_questionary_complete},
    )


def on_telegram_name_confirm(user_name: str, channel: str | None = None) -> AppResponse:
    display = format_display_name(user_name, with_at=True)
    confirm = message("telegram_name_confirm", channel, display=display)
    return AppResponse(
        text=f"{message('start_intro', channel)}\n\n{confirm}",
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


def on_learn_more_hub(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=learn_more_hub_text(channel),
        buttons=[back_to_menu_button(channel), *learn_more_question_buttons(channel)],
        screen=Screen.LEARN_MORE,
    )


def on_learn_more_answer(item: int, channel: str | None = None) -> AppResponse:
    title = learn_more_question_title(item, channel)
    body = learn_more_answer_text(item, channel)
    return AppResponse(
        text=f"**{title}**\n\n{body}",
        buttons=learn_more_answer_buttons(channel),
        screen=Screen.LEARN_MORE_ANSWER,
        meta={"learn_more_item": item},
    )


def on_learn_more_reminder(channel: str | None = None) -> AppResponse:
    return on_learn_more_hub(channel)


def on_learn_more_answer_reminder(
    item: int,
    channel: str | None = None,
) -> AppResponse:
    return on_learn_more_answer(item, channel)


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
    return_later_label = return_later_button(channel)
    input_mode = question_input_mode(question)
    return AppResponse(
        text=message(
            "main_question_prompt",
            channel,
            remaining=remaining,
            time=time_est,
            q_num=int(question["num"]),
            q_text=question["text"],
        ),
        buttons=list(question["variants"]) + [return_later_label],
        screen=Screen.MAIN_QUESTIONARY,
        meta={
            "qv_number": int(question["num"]),
            "qv_id": question["id"],
            "input_mode": input_mode,
            "return_later_label": return_later_label,
        },
    )


def on_main_questionary_complete(
    *,
    rv: int,
    sv: int,
    channel: str | None = None,
    unknown_count: int = 0,
) -> AppResponse:
    intro = message("main_questionary_complete_intro", channel)
    indices = format_indices_summary(float(rv), float(sv))
    parts = [intro, indices]
    if unknown_count > 5:
        parts.append(message("main_questionary_indices_inaccurate_warning", channel))
    outro = message("main_questionary_complete_outro", channel)
    parts.append(outro)
    return AppResponse(
        text="\n\n".join(parts),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": True},
    )


def on_secondary_question_show(
    question: dict[str, Any],
    *,
    remaining: int,
    channel: str | None = None,
    show_intro: bool = False,
) -> AppResponse:
    time_est = estimate_minutes(remaining)
    return_later_label = return_later_button(channel)
    input_mode = question_input_mode(question)
    if show_intro:
        intro = message(
            "secondary_questionary_intro",
            channel,
            remaining=remaining,
            time=time_est,
        )
        body = message(
            "secondary_question_body",
            channel,
            q_num=int(question["num"]),
            q_text=question["text"],
        )
        prompt = f"{intro}\n\n{body}"
    else:
        prompt = message(
            "secondary_question_prompt",
            channel,
            remaining=remaining,
            time=time_est,
            q_num=int(question["num"]),
            q_text=question["text"],
        )
    return AppResponse(
        text=prompt,
        buttons=list(question["variants"]) + [return_later_label],
        screen=Screen.SECONDARY_QUESTIONARY,
        meta={
            "qv_number": int(question["num"]),
            "qv_id": question["id"],
            "input_mode": input_mode,
            "return_later_label": return_later_label,
        },
    )


def on_secondary_questionary_complete(channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=message("secondary_questionary_complete", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
    )


def on_find_country(
    *,
    rv: float,
    sv: float,
    country_code: str,
    country_rv: float,
    country_sv: float,
    channel: str | None = None,
) -> AppResponse:
    indices = format_indices_summary(float(rv), float(sv))
    country_line = message(
        "find_country_result",
        channel,
        country_code=country_code,
        country_rv=country_rv,
        country_sv=country_sv,
    )
    return AppResponse(
        text=f"{indices}\n\n{country_line}",
        buttons=[back_to_menu_button(channel)],
        screen=Screen.FIND_COUNTRY,
        meta={
            "user_rv": rv,
            "user_sv": sv,
            "country_code": country_code,
            "show_country_plot": True,
        },
    )


def on_find_own_place(text: str, channel: str | None = None) -> AppResponse:
    return AppResponse(
        text=text,
        buttons=[back_to_menu_button(channel)],
        screen=Screen.FIND_OWN_PLACE,
    )


def on_find_own_place_need_secondary(
    channel: str | None = None,
    *,
    main_questionary_complete: bool = False,
) -> AppResponse:
    return AppResponse(
        text=message("find_own_place_need_secondary", channel),
        buttons=menu_buttons(channel),
        screen=Screen.MAIN_MENU,
        meta={"main_questionary_complete": main_questionary_complete},
    )


def on_analytics_no_data(channel: str | None = None, *, screen: Screen) -> AppResponse:
    return AppResponse(
        text=message("analytics_no_data", channel),
        buttons=[back_to_menu_button(channel)],
        screen=screen,
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
        buttons[0].casefold(): "learn_more",
        buttons[1].casefold(): "option_1",
        buttons[2].casefold(): "option_2",
        buttons[3].casefold(): "option_3",
        buttons[4].casefold(): "option_4",
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
    "is_back_to_learn_more",
    "is_back_to_menu",
    "is_return_later",
    "learn_more_answer_buttons",
    "learn_more_question_buttons",
    "match_learn_more_question",
    "match_menu_button",
    "on_learn_more_answer",
    "on_learn_more_hub",
    "on_learn_more_answer_reminder",
    "on_learn_more_reminder",
    "on_change_name_prompt",
    "on_empty_name",
    "on_feature_locked",
    "on_feature_stub",
    "on_find_country",
    "on_find_own_place",
    "on_find_own_place_need_secondary",
    "on_analytics_no_data",
    "on_main_answer_empty",
    "on_main_answer_invalid",
    "on_main_menu_reminder",
    "on_main_question_show",
    "on_main_questionary_complete",
    "on_name_entered",
    "on_secondary_question_show",
    "on_secondary_questionary_complete",
    "on_start",
    "on_telegram_name_confirm",
]
