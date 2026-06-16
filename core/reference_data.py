# coding: utf-8
"""Загрузка справочных CSV (gen_sample, country_data) в postgres."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.db import postgres_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GEN_SAMPLE_COLUMNS = [
    "D_INTERVIEW",
    "B_COUNTRY_ALPHA",
    "Q260",
    "Q262",
    "Q173",
    "Q45",
    "Q69",
    "Q6",
    "Q27",
    "Q70",
    "Q65",
    "Q17",
    "Q8",
    "Q11",
    "Q30",
    "Q29",
    "Q33",
    "Q152",
    "insert_time",
]

COUNTRY_DATA_COLUMNS = [
    "country_code",
    "country_rv",
    "country_sv",
    "cluster",
    "name",
    "alpha-2",
    "alpha-3",
    "country-code",
    "iso_3166-2",
    "region",
    "sub-region",
    "intermediate-region",
    "region-code",
    "sub-region-code",
    "intermediate-region-code",
    "insert_time",
]


def _quote_identifier(name: str) -> str:
    return f'"{name}"'


def _table_columns(columns: list[str]) -> str:
    return ", ".join(_quote_identifier(column) for column in columns)


def ensure_reference_schema(logging_config: dict[str, Any]) -> None:
    sql_path = PROJECT_ROOT / "sql" / "005_reference_schema.sql"
    sql_text = sql_path.read_text(encoding="utf-8")
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)


def _copy_csv(
    logging_config: dict[str, Any],
    *,
    schema: str,
    table: str,
    csv_path: Path,
    columns: list[str],
    truncate: bool,
) -> int:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Не найден файл {csv_path}")

    qualified = f"{schema}.{table}"
    col_list = _table_columns(columns)
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            if truncate:
                cur.execute(f"TRUNCATE TABLE {qualified}")
            with csv_path.open("r", encoding="utf-8") as handle:
                copy_sql = (
                    f"COPY {qualified} ({col_list}) "
                    f"FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                )
                cur.copy_expert(copy_sql, handle)
            cur.execute(f"SELECT COUNT(*)::int FROM {qualified}")
            row = cur.fetchone()
    return int(row[0]) if row else 0


def load_reference_data(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "tl",
    gen_sample_path: Path | None = None,
    country_data_path: Path | None = None,
    truncate: bool = True,
) -> dict[str, int]:
    """
    Создаёт таблицы справочников и заливает CSV.

    :return: число строк в gen_sample и country_data после загрузки
    """
    ensure_reference_schema(logging_config)

    gen_path = gen_sample_path or (PROJECT_ROOT / "gen_sample.csv")
    country_path = country_data_path or (PROJECT_ROOT / "country_data.csv")

    gen_count = _copy_csv(
        logging_config,
        schema=reference_schema,
        table="gen_sample",
        csv_path=gen_path,
        columns=GEN_SAMPLE_COLUMNS,
        truncate=truncate,
    )
    country_count = _copy_csv(
        logging_config,
        schema=reference_schema,
        table="country_data",
        csv_path=country_path,
        columns=COUNTRY_DATA_COLUMNS,
        truncate=truncate,
    )
    return {"gen_sample": gen_count, "country_data": country_count}


def reference_data_status(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "tl",
) -> dict[str, int | None]:
    """Возвращает число строк в справочниках или None, если таблицы нет."""
    result: dict[str, int | None] = {"gen_sample": None, "country_data": None}
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            for table in result:
                try:
                    cur.execute(f"SELECT COUNT(*)::int FROM {reference_schema}.{table}")
                    row = cur.fetchone()
                    result[table] = int(row[0]) if row else 0
                except Exception:
                    conn.rollback()
    return result
