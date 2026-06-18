# coding: utf-8
"""Раздел «Узнать больше»: вопросы и ответы FAQ."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.messages import back_to_learn_more_button, back_to_menu_button, message

FAQ_PATH = Path(__file__).resolve().parents[1] / "data" / "learn_more_faq.json"
LEARN_MORE_COUNT = 8


@lru_cache(maxsize=1)
def _load_faq_items() -> list[dict[str, str]]:
    with FAQ_PATH.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return list(data["items"])


def learn_more_question_buttons(channel: str | None = None) -> list[str]:
    """Подписи кнопок вопросов (1–8)."""
    _ = channel
    return [str(item["button"]) for item in _load_faq_items()]


def learn_more_answer_text(item: int, channel: str | None = None) -> str:
    """Текст ответа по номеру вопроса (1–8)."""
    _ = channel
    if item < 1 or item > LEARN_MORE_COUNT:
        raise IndexError(f"learn_more item out of range: {item}")
    return str(_load_faq_items()[item - 1]["answer"])


def learn_more_question_title(item: int, channel: str | None = None) -> str:
    _ = channel
    return learn_more_question_buttons()[item - 1]


def match_learn_more_question(text: str, channel: str | None = None) -> int | None:
    normalized = text.strip().casefold()
    for index, label in enumerate(learn_more_question_buttons(channel), start=1):
        if label.casefold() == normalized:
            return index
    return None


def is_back_to_learn_more(text: str, channel: str | None = None) -> bool:
    return text.strip().casefold() == back_to_learn_more_button(channel).casefold()


def learn_more_answer_buttons(channel: str | None = None) -> list[str]:
    return [back_to_learn_more_button(channel), back_to_menu_button(channel)]


def learn_more_hub_text(channel: str | None = None) -> str:
    return message("learn_more_intro", channel)
