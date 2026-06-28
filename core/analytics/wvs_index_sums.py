# coding: utf-8
"""
Единая методология суммирования индексов RV/SV.

Цель:
    Одинаковый расчёт для ответов бота (текст), строк gen_sample (коды WVS)
    и агрегатов country_data (среднее по стране).

Правило:
    «Не знаю» и прочие missing-коды WVS (≤0, −1…−5) не входят в сумму.
    Индекс по группе считается, только если есть хотя бы один валидный пункт.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# Согласовано с core/analytics/indices.py
RV_QV_IDS: tuple[str, ...] = ("Q17", "Q8", "Q11", "Q30", "Q29", "Q33", "Q152")
SV_QV_IDS: tuple[str, ...] = ("Q173", "Q45", "Q69", "Q6", "Q27", "Q70", "Q65")

WVS_MISSING_CODES = frozenset({-1, -2, -3, -4, -5})

GEN_SAMPLE_INDEX_COLUMNS: tuple[str, ...] = RV_QV_IDS + SV_QV_IDS


def is_valid_wvs_code(value: Any) -> bool:
    """True для substantive кодов WVS (обычно 1–4)."""
    if value is None:
        return False
    try:
        code = int(value)
    except (TypeError, ValueError):
        return False
    if code in WVS_MISSING_CODES or code <= 0:
        return False
    return True


def sum_group(values: dict[str, Any], qv_ids: tuple[str, ...]) -> int | None:
    """Сумма валидных кодов по группе вопросов или None, если валидных нет."""
    total = 0
    found = False
    for qv_id in qv_ids:
        if qv_id not in values:
            continue
        raw = values[qv_id]
        if not is_valid_wvs_code(raw):
            continue
        total += int(raw)
        found = True
    return total if found else None


def compute_rv_sv_from_codes(codes: dict[str, Any]) -> tuple[int, int] | None:
    """
    RV/SV из словаря {Q173: 2, Q17: 1, ...}.

    :return: (rv, sv) или None, если нет хотя бы одного валидного пункта в каждой группе
    """
    rv = sum_group(codes, RV_QV_IDS)
    sv = sum_group(codes, SV_QV_IDS)
    if rv is None or sv is None:
        return None
    return rv, sv


def aggregate_country_means(
    rows: list[tuple[str, int, int]],
) -> dict[str, tuple[float, float]]:
    """
    Средние RV/SV по стране из списка (country_code, rv, sv).

    :return: {country_code: (country_rv, country_sv)} округлённо до 2 знаков
    """
    buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for country_code, rv, sv in rows:
        buckets[str(country_code).upper()].append((rv, sv))
    result: dict[str, tuple[float, float]] = {}
    for code, pairs in buckets.items():
        if not pairs:
            continue
        mean_rv = sum(p[0] for p in pairs) / len(pairs)
        mean_sv = sum(p[1] for p in pairs) / len(pairs)
        result[code] = (round(mean_rv, 2), round(mean_sv, 2))
    return result
