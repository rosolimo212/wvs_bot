# coding: utf-8
"""
Загрузка справочных таблиц WVS в PostgreSQL.

Цель:
    Создать gen_sample и country_data, залить CSV и обогатить country_data
    полями профиля из data/country_profiles.json.

Вход:
    gen_sample.csv, country_data.csv в корне проекта (или пути через аргументы).
    config.yaml с logging_enabled: true.

Выход:
    Таблицы {schema}.gen_sample и {schema}.country_data с данными.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.analytics.wvs_index_sums import (
    GEN_SAMPLE_INDEX_COLUMNS,
    aggregate_country_means,
    compute_rv_sv_from_codes,
)
from core.country_profiles import load_country_profiles
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

COUNTRY_PROFILE_COLUMNS = (
    "full_name",
    "government_type",
    "gdp_per_capita_usd",
    "population",
    "flight_hours_from_london",
)


def _quote_identifier(name: str) -> str:
    return f'"{name}"'


def _table_columns(columns: list[str]) -> str:
    return ", ".join(_quote_identifier(column) for column in columns)


def _reference_schema_sql(sql_text: str, reference_schema: str) -> str:
    if reference_schema != "wvs":
        sql_text = sql_text.replace("wvs.", f"{reference_schema}.")
        sql_text = sql_text.replace(
            "CREATE SCHEMA IF NOT EXISTS wvs",
            f"CREATE SCHEMA IF NOT EXISTS {reference_schema}",
        )
    return sql_text


def ensure_reference_schema(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> None:
    """Создаёт схему и таблицы gen_sample, country_data (IF NOT EXISTS)."""
    sql_path = PROJECT_ROOT / "sql" / "005_reference_schema.sql"
    sql_text = _reference_schema_sql(sql_path.read_text(encoding="utf-8"), reference_schema)
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)
            for column, ddl in (
                ("full_name", "TEXT"),
                ("government_type", "TEXT"),
                ("gdp_per_capita_usd", "BIGINT"),
                ("population", "BIGINT"),
                ("flight_hours_from_london", "NUMERIC(5, 1)"),
            ):
                cur.execute(
                    f"ALTER TABLE {reference_schema}.country_data "
                    f"ADD COLUMN IF NOT EXISTS {column} {ddl}"
                )


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


def enrich_country_data_from_profiles(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
    profiles_path: Path | None = None,
) -> int:
    """
    Обновляет country_data полями из country_profiles.json.

    :return: число обновлённых строк
    """
    profiles = load_country_profiles(
        str(profiles_path) if profiles_path is not None else None
    )
    updated = 0
    qualified = f"{reference_schema}.country_data"
    sql = f"""
        UPDATE {qualified}
        SET
            full_name = %s,
            government_type = %s,
            gdp_per_capita_usd = %s,
            population = %s,
            flight_hours_from_london = %s
        WHERE country_code = %s
    """
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            for country_code, profile in profiles.items():
                cur.execute(
                    sql,
                    (
                        profile.get("full_name"),
                        profile.get("government_type"),
                        profile.get("gdp_per_capita_usd"),
                        profile.get("population"),
                        profile.get("flight_hours_from_london"),
                        country_code,
                    ),
                )
                updated += cur.rowcount
    return updated


def recompute_country_indices_from_gen_sample(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> int:
    """
    Пересчитывает country_rv / country_sv в country_data как среднее RV/SV
    респондентов gen_sample (missing «не знаю» не входят в сумму респондента).

    :return: число обновлённых строк country_data
    """
    q_cols = ", ".join(f'"{name}"' for name in GEN_SAMPLE_INDEX_COLUMNS)
    query = f"""
        SELECT "B_COUNTRY_ALPHA", {q_cols}
        FROM {reference_schema}.gen_sample
        WHERE "B_COUNTRY_ALPHA" IS NOT NULL
    """
    respondent_rows: list[tuple[str, int, int]] = []
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            for row in cur.fetchall():
                country_code = str(row[0]).upper()
                codes = {
                    name: row[1 + index]
                    for index, name in enumerate(GEN_SAMPLE_INDEX_COLUMNS)
                }
                indices = compute_rv_sv_from_codes(codes)
                if indices is None:
                    continue
                rv, sv = indices
                respondent_rows.append((country_code, rv, sv))

    country_means = aggregate_country_means(respondent_rows)
    if not country_means:
        return 0

    qualified = f"{reference_schema}.country_data"
    update_sql = f"""
        UPDATE {qualified}
        SET country_rv = %s, country_sv = %s
        WHERE country_code = %s
    """
    updated = 0
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            for country_code, (country_rv, country_sv) in country_means.items():
                cur.execute(update_sql, (country_rv, country_sv, country_code))
                updated += cur.rowcount
    return updated


def setup_reference_tables(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
    gen_sample_path: Path | None = None,
    country_data_path: Path | None = None,
    profiles_path: Path | None = None,
    truncate: bool = True,
    load_csv: bool = True,
    enrich_profiles: bool = True,
) -> dict[str, int | None]:
    """
    Полный цикл: DDL → CSV → обогащение профилями.

    :return: счётчики gen_sample, country_data, profile_updates
    """
    ensure_reference_schema(logging_config, reference_schema=reference_schema)

    result: dict[str, int | None] = {
        "gen_sample": None,
        "country_data": None,
        "country_index_updates": None,
        "profile_updates": None,
    }

    if load_csv:
        gen_path = gen_sample_path or (PROJECT_ROOT / "gen_sample.csv")
        country_path = country_data_path or (PROJECT_ROOT / "country_data.csv")
        result["gen_sample"] = _copy_csv(
            logging_config,
            schema=reference_schema,
            table="gen_sample",
            csv_path=gen_path,
            columns=GEN_SAMPLE_COLUMNS,
            truncate=truncate,
        )
        result["country_data"] = _copy_csv(
            logging_config,
            schema=reference_schema,
            table="country_data",
            csv_path=country_path,
            columns=COUNTRY_DATA_COLUMNS,
            truncate=truncate,
        )
        result["country_index_updates"] = recompute_country_indices_from_gen_sample(
            logging_config,
            reference_schema=reference_schema,
        )

    if enrich_profiles:
        result["profile_updates"] = enrich_country_data_from_profiles(
            logging_config,
            reference_schema=reference_schema,
            profiles_path=profiles_path,
        )

    return result


def load_reference_data(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
    gen_sample_path: Path | None = None,
    country_data_path: Path | None = None,
    profiles_path: Path | None = None,
    truncate: bool = True,
) -> dict[str, int | None]:
    """Совместимость: создать таблицы, залить CSV, обогатить профилями."""
    return setup_reference_tables(
        logging_config,
        reference_schema=reference_schema,
        gen_sample_path=gen_sample_path,
        country_data_path=country_data_path,
        profiles_path=profiles_path,
        truncate=truncate,
        load_csv=True,
        enrich_profiles=True,
    )


def reference_data_status(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
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
