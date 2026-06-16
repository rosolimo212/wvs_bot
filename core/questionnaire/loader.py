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
    return list(questions_data["main_questions"])
