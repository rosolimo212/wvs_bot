# coding: utf-8
"""Загрузка и адаптация SQL-запросов аналитики."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.db import postgres_connection

SQL_ROOT = Path(__file__).resolve().parents[2]


def adapt_sql(
    sql: str,
    *,
    user_schema: str,
    reference_schema: str = "tl",
) -> str:
    sql = sql.replace("tl.user_answers", f"{user_schema}.user_answers")
    sql = sql.replace("tl.user_reviews", f"{user_schema}.user_reviews")
    sql = sql.replace("tl.gen_sample", f"{reference_schema}.gen_sample")
    sql = sql.replace("tl.country_data", f"{reference_schema}.country_data")
    return sql.replace("[0-results_str9]+", "[0-9]+")


def load_sql(
    filename: str,
    *,
    user_schema: str,
    reference_schema: str = "tl",
) -> str:
    sql = (SQL_ROOT / filename).read_text(encoding="utf-8")
    return adapt_sql(sql, user_schema=user_schema, reference_schema=reference_schema)


def fetch_one_row(
    query: str,
    logging_config: dict[str, Any],
) -> tuple[Any, ...] | None:
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()


def fetch_all_rows(
    query: str,
    logging_config: dict[str, Any],
) -> list[tuple[Any, ...]]:
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return list(cur.fetchall())
