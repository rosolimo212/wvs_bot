# coding: utf-8
"""
Поиск ближайшей страны по индексам ценностей.

Цель:
    Euclidean distance в (RV, SV) между пользователем и country_data.

Вход:
    answer_store, user_id, logging_config.

Выход:
    NearestCountry или None, если индексы пользователя не посчитались.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.analytics.indices import compute_main_indices
from core.analytics.sql import fetch_all_rows
from core.questionnaire.base import MainAnswerStore


@dataclass(frozen=True)
class NearestCountry:
    rv: float
    sv: float
    country_code: str
    country_rv: float
    country_sv: float


def find_nearest_country(
    answer_store: MainAnswerStore,
    user_id: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> NearestCountry | None:
    indices = compute_main_indices(answer_store, user_id)
    if indices is None:
        return None
    user_rv, user_sv = indices

    query = f"""
        SELECT country_code, country_rv, country_sv
        FROM {reference_schema}.country_data
        WHERE country_code != 'EGY'
          AND country_rv IS NOT NULL
          AND country_sv IS NOT NULL
    """
    best: NearestCountry | None = None
    best_dist: float | None = None
    for row in fetch_all_rows(query, logging_config):
        country_code = str(row[0])
        country_rv = float(row[1])
        country_sv = float(row[2])
        dist = (user_rv - country_rv) ** 2 + (user_sv - country_sv) ** 2
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = NearestCountry(
                rv=float(user_rv),
                sv=float(user_sv),
                country_code=country_code,
                country_rv=country_rv,
                country_sv=country_sv,
            )
    return best
