# coding: utf-8
"""Расчёт индексов RV/SV по ответам основной анкеты (логика count_ind.sql)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.db import postgres_connection
from core.questionnaire.base import MainAnswerStore

RV_QV_IDS = frozenset({"Q17", "Q8", "Q11", "Q30", "Q29", "Q33", "Q152"})
SV_QV_IDS = frozenset({"Q173", "Q45", "Q69", "Q6", "Q27", "Q70", "Q65"})
_NUMBER_RE = re.compile(r"^[+-]?\d+")


def answer_value(qv_id: str, answer_text: str) -> int:
    text = answer_text.strip()
    lower = text.casefold()
    if lower in {"не знаю", "-1. не знаю"} or text.startswith("-1."):
        return -1
    if qv_id == "Q17":
        return 1 if "ослуш" in lower else 2
    match = _NUMBER_RE.match(text.lstrip())
    if match:
        return int(match.group(0))
    return -1


def compute_indices_from_answers(answers: list[dict[str, Any]]) -> tuple[int, int] | None:
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


def load_count_ind_sql(schema: str) -> str:
    root = Path(__file__).resolve().parents[2]
    sql = (root / "count_ind.sql").read_text(encoding="utf-8")
    sql = sql.replace("tl.user_answers", f"{schema}.user_answers")
    sql = sql.replace("[0-results_str9]+", "[0-9]+")
    return sql


def compute_indices_from_postgres(user_id: str, logging_config: dict[str, Any]) -> tuple[int, int] | None:
    schema = logging_config["schema"]
    query = load_count_ind_sql(schema).format(user_id=user_id)
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()
    if row is None:
        return None
    return int(row[2]), int(row[3])


def compute_main_indices(
    answer_store: MainAnswerStore,
    user_id: str,
    *,
    logging_config: dict[str, Any] | None = None,
) -> tuple[int, int] | None:
    if logging_config is not None:
        try:
            return compute_indices_from_postgres(user_id, logging_config)
        except Exception:
            pass
    answers = answer_store.list_answers(user_id)
    return compute_indices_from_answers(answers)
