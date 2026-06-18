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
    Особая обработка Q11/Q17 (текст про качества детей) и «Не знаю» — см. answer_value().
"""

from __future__ import annotations

import re
from typing import Any

from core.analytics.child_qualities import text_mentions_imagination, text_mentions_obedience
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
        return 1 if text_mentions_obedience(text) else 2
    if qv_id == "Q11":
        return 1 if text_mentions_imagination(text) else 2
    match = _NUMBER_RE.match(text.lstrip())
    if match:
        return int(match.group(0))
    return -1


UNKNOWN_ANSWER_WARN_THRESHOLD = 5


def count_unknown_main_answers(answers: list[dict[str, Any]]) -> int:
    """Считает ответы «Не знаю» (-1) в основной анкете."""
    total = 0
    for row in answers:
        qv_id = str(row["qv_id"])
        if answer_value(qv_id, str(row["answer_text"])) == -1:
            total += 1
    return total


def should_warn_inaccurate_indices(unknown_count: int) -> bool:
    return unknown_count > UNKNOWN_ANSWER_WARN_THRESHOLD


def compute_indices_from_answers(answers: list[dict[str, Any]]) -> tuple[int, int] | None:
    """
    Считает RV и SV по уже загруженным ответам.

    :param answers: записи с ключами qv_id, answer_text
    :return: (rv, sv) или None, если нет ответов обеих групп
    """
    by_id = {str(row["qv_id"]): str(row["answer_text"]) for row in answers}
    child_qualities_text = by_id.get("Q17") or by_id.get("Q11")

    rv = 0
    sv = 0
    has_rv = False
    has_sv = False
    counted_rv: set[str] = set()
    for row in answers:
        qv_id = str(row["qv_id"])
        value = answer_value(qv_id, str(row["answer_text"]))
        if qv_id in RV_QV_IDS:
            rv += value
            has_rv = True
            counted_rv.add(qv_id)
        elif qv_id in SV_QV_IDS:
            sv += value
            has_sv = True

    if "Q11" in RV_QV_IDS and "Q11" not in counted_rv and child_qualities_text:
        rv += answer_value("Q11", child_qualities_text)
        has_rv = True
    if "Q17" in RV_QV_IDS and "Q17" not in counted_rv and child_qualities_text:
        rv += answer_value("Q17", child_qualities_text)
        has_rv = True
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
