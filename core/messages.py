# coding: utf-8
"""
Тексты диалогов с пользователем (data/dialog_messages.json).

Цель:
    Вынести все user-facing строки из кода в JSON для правки и локализации.

Вход:
    name сообщения, channel (streamlit→browser, telegram, console), placeholders.

Выход:
    Готовая строка; для telegram/browser можно задать override в JSON.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_MESSAGES_PATH = Path(__file__).resolve().parents[1] / "data" / "dialog_messages.json"

CHANNEL_TO_UI_KEY = {
    "console": "console",
    "telegram": "telegram",
    "streamlit": "browser",
}


@lru_cache(maxsize=1)
def _load_catalog(path: str | None = None) -> dict[str, Any]:
    file_path = Path(path) if path else DEFAULT_MESSAGES_PATH
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_channel_key(channel: str | None) -> str | None:
    if channel is None:
        return None
    return CHANNEL_TO_UI_KEY.get(channel, channel)


def _pick_text(entry: dict[str, Any], channel: str | None) -> str:
    ui_key = _resolve_channel_key(channel)
    if ui_key:
        override = str(entry.get(ui_key, "") or "").strip()
        if override:
            return override
    return str(entry["default"])


def _find_by_name(section: str, name: str, path: str | None = None) -> dict[str, Any]:
    catalog = _load_catalog(path)
    for item in catalog.get(section, []):
        if item.get("name") == name:
            return item
    raise KeyError(f"Не найден {section} name={name!r} в dialog_messages.json")


def message(
    name: str,
    channel: str | None = None,
    *,
    path: str | None = None,
    **placeholders: Any,
) -> str:
    entry = _find_by_name("messages", name, path)
    text = _pick_text(entry, channel)
    if placeholders:
        text = text.format(**placeholders)
    return text


def button(
    name: str,
    channel: str | None = None,
    *,
    path: str | None = None,
) -> str:
    entry = _find_by_name("buttons", name, path)
    return _pick_text(entry, channel)


def menu_buttons(channel: str | None = None, *, path: str | None = None) -> list[str]:
    return [
        button("menu_option_learn_more", channel, path=path),
        button("menu_option_1", channel, path=path),
        button("menu_option_2", channel, path=path),
        button("menu_option_3", channel, path=path),
        button("menu_option_4", channel, path=path),
    ]


def back_to_menu_button(channel: str | None = None) -> str:
    return button("back_to_menu", channel)


def back_to_learn_more_button(channel: str | None = None) -> str:
    return button("back_to_learn_more", channel)


def confirm_name_button(channel: str | None = None) -> str:
    return button("confirm_name", channel)


def change_name_button(channel: str | None = None) -> str:
    return button("change_name", channel)


def custom_answer_button(channel: str | None = None) -> str:
    return button("custom_answer", channel)


def return_later_button(channel: str | None = None) -> str:
    return button("return_later", channel)


MENU_BUTTONS = menu_buttons()
BACK_TO_MENU_BUTTON = back_to_menu_button()
CONFIRM_NAME_BUTTON = confirm_name_button()
CHANGE_NAME_BUTTON = change_name_button()
CUSTOM_ANSWER_BUTTON = custom_answer_button()
RETURN_LATER_BUTTON = return_later_button()
