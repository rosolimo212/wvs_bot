# coding: utf-8
"""
Расчёт индексов RV и SV по ответам основной анкеты.

Цель:
    Получить два числовых показателя ценностей пользователя в той же логике,
    что использовалась в старом count_ind.sql, но без SQL-запроса.

Вход:
    Список ответов из хранилища анкеты (user_answers) или memory-store в тестах.

Выход:
    Пара (rv, sv) — суммы кодированных ответов по двум группам вопросов.
    None, если не хватает ответов для расчёта.

Группы вопросов:
    RV — традиционные / секулярно-рациональные ценности.
    SV — ценности выживания / самовыражения.

Риски:
    Особая обработка Q17 (текстовый ответ) и варианта «Не знаю» — см. answer_value().
"""

from __future__ import annotations

import re
from typing import Any

from core.questionnaire.base import MainAnswerStore

# Вопросы, входящие в индекс RV (см. questions.json, секция main_questions).
RV_QV_IDS = frozenset({"Q17", "Q8", "Q11", "Q30", "Q29", "Q33", "Q152"})
# Вопросы, входящие в индекс SV.
SV_QV_IDS = frozenset({"Q173", "Q45", "Q69", "Q6", "Q27", "Q70", "Q65"})
_NUMBER_RE = re.compile(r"^[+-]?\d+")


def answer_value(qv_id: str, answer_text: str) -> int:
    """
    Преобразует текст ответа в числовой код для суммирования.

    :param qv_id: идентификатор вопроса (например Q17)
    :param answer_text: то, что выбрал или написал пользователь
    :return: число для индекса; -1 для «Не знаю»
    """
    text = answer_text.strip()
    lower = text.casefold()
    if lower in {"не знаю", "-1. не знаю"} or text.startswith("-1."):
        return -1
    if qv_id == "Q17":
        # Текстовый вопрос: «послушание» → 1, остальное → 2.
        return 1 if "ослуш" in lower else 2
    match = _NUMBER_RE.match(text.lstrip())
    if match:
        return int(match.group(0))
    return -1


def compute_indices_from_answers(answers: list[dict[str, Any]]) -> tuple[int, int] | None:
    """
    Считает RV и SV по уже загруженным ответам.

    :param answers: записи с ключами qv_id, answer_text
    :return: (rv, sv) или None, если нет ответов обеих групп
    """
    rv = 0
    sv = 0
    has_rv = False
    has_sv = False
    for row in answers:
        qv_id = str(row["qv_id"])
        value = answer_value(qv_id, str(row["answer_text"]))
        if qv_id in RV_QV_IDS:
            rv += value
            has_rv = True
        elif qv_id in SV_QV_IDS:
            sv += value
            has_sv = True
    if not has_rv or not has_sv:
        return None
    return rv, sv


def compute_main_indices(
    answer_store: MainAnswerStore,
    user_id: str,
    *,
    logging_config: dict[str, Any] | None = None,
) -> tuple[int, int] | None:
    """
    Единая точка расчёта индексов для AppService.

    Всегда читает ответы через answer_store и считает в Python.
    Параметр logging_config оставлен для совместимости вызовов и не используется.

    :param answer_store: postgres или memory
    :param user_id: hash пользователя
    :return: (rv, sv) или None
    """
    _ = logging_config
    answers = answer_store.list_answers(user_id)
    return compute_indices_from_answers(answers)
