# coding: utf-8
"""Сравнение индексов пользователя с выборкой WVS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.analytics.sql import fetch_one_row, load_sql


@dataclass(frozen=True)
class UserPosition:
    rv: float
    sv: float
    rv_rank: int
    sv_rank: int


def _to_percent_rank(value: float) -> int:
    return int(round(float(value) * 100))


def _load_position(
    filename: str,
    user_id: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
    rv_index: int = 2,
    sv_index: int = 3,
) -> UserPosition | None:
    schema = logging_config["schema"]
    query = load_sql(
        filename,
        user_schema=schema,
        reference_schema=reference_schema,
    ).format(user_id=user_id)
    row = fetch_one_row(query, logging_config)
    if row is None:
        return None
    return UserPosition(
        rv=float(row[rv_index]),
        sv=float(row[sv_index]),
        rv_rank=_to_percent_rank(row[-2]),
        sv_rank=_to_percent_rank(row[-1]),
    )


def find_global_position(
    user_id: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> UserPosition | None:
    return _load_position(
        "count_pos.sql",
        user_id,
        logging_config,
        reference_schema=reference_schema,
    )


def find_age_position(
    user_id: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> UserPosition | None:
    return _load_position(
        "age_strat.sql",
        user_id,
        logging_config,
        reference_schema=reference_schema,
        rv_index=0,
        sv_index=1,
    )


def find_gender_age_position(
    user_id: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> UserPosition | None:
    return _load_position(
        "gender_age_strat.sql",
        user_id,
        logging_config,
        reference_schema=reference_schema,
        rv_index=0,
        sv_index=1,
    )
