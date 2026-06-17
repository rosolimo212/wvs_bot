# coding: utf-8
"""
Консольный клиент WVS.

Цель:
    Отладка сценария без Streamlit и Telegram. График страны не выводится —
    только текстовый результат и карточка страны.

Вход:
    config.yaml (секции app, logging, paths, analytics).

Выход:
    Интерактивный диалог в stdin/stdout до команды «0» / «выход».
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.messages import button, message
from core.models import Screen
from ui.base import build_app_service
from ui.helpers import apply_response, get_identity, init_user_identity
from ui.interactive_client import (
    console_plot_note,
    handle_name_entered,
    handle_raw_input,
    is_questionnaire_screen,
    questionnaire_actions,
    questionnaire_choice_buttons,
    return_later_from_questionnaire,
    submit_questionnaire_answer,
    sync_profile_from_db,
)


def _print_response(state: dict[str, Any], channel: str = "console") -> None:
    print()
    print(state.get("last_text", ""))
    screen = state.get("screen", "")
    if screen == Screen.FIND_COUNTRY.value and state.get("meta", {}).get("show_country_plot"):
        print()
        print(console_plot_note(channel))
    print()


def _read_exit(choice: str) -> bool:
    return choice.lower() in ("0", "exit", "quit", "выход")


def _handle_questionnaire_input(
    service,
    identity,
    channel: str,
    state: dict[str, Any],
    text: str,
) -> None:
    screen = state.get("screen", "")
    meta = state.get("meta", {})
    return_later_label = meta.get("return_later_label", button("return_later", channel))
    answer_action, return_action = questionnaire_actions(screen)

    if text == return_later_label:
        return_later_from_questionnaire(
            service,
            identity,
            channel,
            state,
            screen=screen,
            return_action=return_action,
        )
        return

    choices = questionnaire_choice_buttons(state, channel)
    input_mode = meta.get("input_mode", "choice")

    if input_mode == "text":
        if text in choices:
            submit_questionnaire_answer(
                service,
                identity,
                channel,
                state,
                screen=screen,
                answer_action=answer_action,
                answer=text,
                selected=text,
            )
        else:
            submit_questionnaire_answer(
                service,
                identity,
                channel,
                state,
                screen=screen,
                answer_action=answer_action,
                answer=text,
                selected="",
            )
        return

    if text not in choices:
        print(message("console_invalid_choice", channel))
        return

    submit_questionnaire_answer(
        service,
        identity,
        channel,
        state,
        screen=screen,
        answer_action=answer_action,
        answer=text,
        selected=text,
    )


def run_console(config: dict[str, Any]) -> None:
    service = build_app_service(config)
    state: dict[str, Any] = {}
    channel = "console"

    identity = init_user_identity(service, state, channel)
    response = service.handle_start(identity, channel)
    sync_profile_from_db(service, identity, state)
    apply_response(state, response)
    state["main_questionary_complete"] = service.is_main_questionary_complete(identity)

    print(message("console_banner", channel))
    print(f"user_id (hash): {state['user_id']}")
    print(f"internal_user_id: {state['internal_user_id']}")
    print(f"external_user_id: {state['external_user_id']}")
    _print_response(state, channel)

    while True:
        screen = state.get("screen", Screen.START.value)
        identity = get_identity(state)

        if screen == Screen.START.value:
            text = input("> ").strip()
            if _read_exit(text):
                break
            handle_name_entered(service, identity, channel, state, text)
            _print_response(state, channel)
            continue

        if is_questionnaire_screen(screen):
            meta = state.get("meta", {})
            input_mode = meta.get("input_mode", "choice")
            choices = questionnaire_choice_buttons(state, channel)
            return_later_label = meta.get("return_later_label", button("return_later", channel))

            print(message("console_menu_header", channel))
            for idx, label in enumerate(choices, start=1):
                print(f"  {idx}. {label}")
            print(f"  {len(choices) + 1}. {return_later_label}")
            if input_mode == "text":
                print(message("console_question_text_hint", channel))
            print("  0. Выход")

            choice = input("> ").strip()
            if _read_exit(choice):
                break

            if choice.isdigit():
                idx = int(choice) - 1
                if idx == len(choices):
                    _handle_questionnaire_input(service, identity, channel, state, return_later_label)
                elif 0 <= idx < len(choices):
                    _handle_questionnaire_input(service, identity, channel, state, choices[idx])
                else:
                    print(message("console_invalid_choice", channel))
                    continue
            else:
                _handle_questionnaire_input(service, identity, channel, state, choice)

            _print_response(state, channel)
            continue

        buttons = state.get("buttons", [])
        if buttons:
            print(message("console_menu_header", channel))
            for idx, label in enumerate(buttons, start=1):
                print(f"  {idx}. {label}")
            print("  0. Выход")

        choice = input("> ").strip()
        if _read_exit(choice):
            break

        if choice.isdigit() and buttons:
            idx = int(choice) - 1
            if 0 <= idx < len(buttons):
                text = buttons[idx]
            else:
                print(message("console_invalid_choice", channel))
                continue
        else:
            text = choice

        handle_raw_input(service, identity, channel, state, text, config=config)
        _print_response(state, channel)

    print(message("console_goodbye", channel))
