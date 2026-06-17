# coding: utf-8
"""Поиск ближайшей страны по индексам ценностей."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.analytics.sql import fetch_one_row, load_sql


@dataclass(frozen=True)
class NearestCountry:
    rv: float
    sv: float
    country_code: str
    country_rv: float
    country_sv: float


def find_nearest_country(
    user_id: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> NearestCountry | None:
    schema = logging_config["schema"]
    query = load_sql(
        "find_country.sql",
        user_schema=schema,
        reference_schema=reference_schema,
    ).format(user_id=user_id)
    row = fetch_one_row(query, logging_config)
    if row is None:
        return None
    return NearestCountry(
        rv=float(row[2]),
        sv=float(row[3]),
        country_code=str(row[4]),
        country_rv=float(row[5]),
        country_sv=float(row[6]),
    )
