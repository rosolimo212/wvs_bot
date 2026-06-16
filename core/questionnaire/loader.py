# coding: utf-8
"""Загрузка вопросов из questions.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_questions(path: str | Path) -> dict[str, Any]:
    """
    Загружает файл анкеты.

    :param path: путь к questions.json
    :return: словарь с ключами main_questions, secondary_questions, dialogs
    """
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "main_questions" not in data:
        raise ValueError(f"В {file_path!r} нет секции main_questions")
    return data


def get_main_questions(questions_data: dict[str, Any]) -> list[dict[str, Any]]:
    return [_normalize_question(question) for question in questions_data["main_questions"]]


def normalize_question_text(text: str) -> str:
    """В исходном JSON перенос строки иногда записан как /n вместо \\n."""
    return text.replace("/n", "\n")


def _normalize_question(question: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(question)
    if "text" in normalized:
        normalized["text"] = normalize_question_text(str(normalized["text"]))
    return normalized


def question_input_mode(question: dict[str, Any]) -> str:
    """
    Режим ввода ответа по структуре вопроса в questions.json.

    choice — только варианты из JSON.
    text — нужен свободный ввод (например, Q17: один вариант «Не знаю»).
    """
    variants = list(question.get("variants", []))
    if len(variants) == 1 and str(variants[0]).strip().startswith("-1"):
        return "text"
    return "choice"
