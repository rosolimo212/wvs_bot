# coding: utf-8
"""
Расчёт индексов RV и SV по ответам основной анкеты.

Цель:
    Получить два числовых показателя ценностей пользователя.

Вход:
    Список ответов из хранилища анкеты (user_answers) или memory-store в тестах.

Выход:
    Пара (rv, sv) — суммы кодированных ответов по двум группам вопросов.
    None, если нет хотя бы одного валидного (не «не знаю») ответа в каждой группе.

Методология:
    «Не знаю» и нераспознанные ответы не входят в сумму (см. wvs_index_sums.py).
    Для gen_sample и country_data используется та же логика по кодам WVS.
"""

from __future__ import annotations

import re
from typing import Any

from core.analytics.child_qualities import text_mentions_imagination, text_mentions_obedience
from core.analytics.wvs_index_sums import RV_QV_IDS, SV_QV_IDS
from core.questionnaire.base import MainAnswerStore

RV_QV_IDS_SET = frozenset(RV_QV_IDS)
SV_QV_IDS_SET = frozenset(SV_QV_IDS)
_NUMBER_RE = re.compile(r"^[+-]?\d+")


def answer_value(qv_id: str, answer_text: str) -> int | None:
    """
    Преобразует текст ответа в числовой код для суммирования.

    :return: 1–4 (или 1–2 для Q11/Q17) либо None для «Не знаю» / нераспознанного
    """
    text = answer_text.strip()
    lower = text.casefold()
    if lower in {"не знаю", "-1. не знаю"} or text.startswith("-1."):
        return None
    if qv_id == "Q17":
        return 1 if text_mentions_obedience(text) else 2
    if qv_id == "Q11":
        return 1 if text_mentions_imagination(text) else 2
    match = _NUMBER_RE.match(text.lstrip())
    if match:
        code = int(match.group(0))
        return code if code > 0 else None
    return None


UNKNOWN_ANSWER_WARN_THRESHOLD = 5


def is_unknown_main_answer(qv_id: str, answer_text: str) -> bool:
    return answer_value(qv_id, answer_text) is None


def count_unknown_main_answers(answers: list[dict[str, Any]]) -> int:
    """Считает ответы «Не знаю» / без кода в основной анкете."""
    total = 0
    for row in answers:
        qv_id = str(row["qv_id"])
        if is_unknown_main_answer(qv_id, str(row["answer_text"])):
            total += 1
    return total


def should_warn_inaccurate_indices(unknown_count: int) -> bool:
    return unknown_count >= UNKNOWN_ANSWER_WARN_THRESHOLD


def _sum_from_coded_values(coded: dict[str, int]) -> tuple[int, int] | None:
    rv_total = 0
    sv_total = 0
    has_rv = False
    has_sv = False
    for qv_id, value in coded.items():
        if qv_id in RV_QV_IDS_SET:
            rv_total += value
            has_rv = True
        elif qv_id in SV_QV_IDS_SET:
            sv_total += value
            has_sv = True
    if not has_rv or not has_sv:
        return None
    return rv_total, sv_total


def compute_indices_from_answers(answers: list[dict[str, Any]]) -> tuple[int, int] | None:
    """
    Считает RV и SV по уже загруженным ответам.

    «Не знаю» пропускается; в сумму попадают только валидные коды.
    """
    by_id = {str(row["qv_id"]): str(row["answer_text"]) for row in answers}
    child_qualities_text = by_id.get("Q17") or by_id.get("Q11")

    coded: dict[str, int] = {}
    for row in answers:
        qv_id = str(row["qv_id"])
        value = answer_value(qv_id, str(row["answer_text"]))
        if value is None:
            continue
        if qv_id in RV_QV_IDS_SET or qv_id in SV_QV_IDS_SET:
            coded[qv_id] = value

    if "Q11" in RV_QV_IDS_SET and "Q11" not in coded and child_qualities_text:
        q11 = answer_value("Q11", child_qualities_text)
        if q11 is not None:
            coded["Q11"] = q11
    if "Q17" in RV_QV_IDS_SET and "Q17" not in coded and child_qualities_text:
        q17 = answer_value("Q17", child_qualities_text)
        if q17 is not None:
            coded["Q17"] = q17

    return _sum_from_coded_values(coded)


def compute_main_indices(
    answer_store: MainAnswerStore,
    user_id: str,
    *,
    logging_config: dict[str, Any] | None = None,
) -> tuple[int, int] | None:
    _ = logging_config
    answers = answer_store.list_answers(user_id)
    return compute_indices_from_answers(answers)
