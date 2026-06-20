# coding: utf-8
"""Сопоставление текста страны с кодом из справочника WVS."""

from __future__ import annotations

from typing import Any

from core.analytics.child_qualities import normalize_match_text
from core.analytics.sql import fetch_all_rows
from core.country_profiles import load_country_profiles

DEFAULT_COUNTRY_CODE = "RUS"


def _add_alias(catalog: dict[str, str], alias: str | None, country_code: str) -> None:
    if not alias:
        return
    key = normalize_match_text(alias)
    if key:
        catalog[key] = country_code.upper()


def build_country_alias_catalog(
    country_rows: list[tuple[Any, ...]] | None = None,
) -> dict[str, str]:
    """
    Строит словарь «нормализованный алиас → country_code».

    Учитывает английские названия из country_data и русские full_name из profiles.
    """
    catalog: dict[str, str] = {}
    profiles = load_country_profiles()

    if country_rows is None:
        return catalog

    for row in country_rows:
        country_code = str(row[0]).upper()
        name = str(row[1] or "")
        alpha2 = str(row[2] or "")
        alpha3 = str(row[3] or "")
        _add_alias(catalog, country_code, country_code)
        _add_alias(catalog, name, country_code)
        _add_alias(catalog, alpha2, country_code)
        _add_alias(catalog, alpha3, country_code)
        profile = profiles.get(country_code)
        if profile:
            _add_alias(catalog, str(profile.get("full_name", "")), country_code)

    return catalog


def load_country_alias_catalog(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> dict[str, str]:
    schema = reference_schema
    query = f"""
        SELECT country_code, name, "alpha-2", "alpha-3"
        FROM {schema}.country_data
    """
    rows = fetch_all_rows(query, logging_config)
    catalog = build_country_alias_catalog(rows)
    for country_code, profile in load_country_profiles().items():
        _add_alias(catalog, country_code, country_code)
        _add_alias(catalog, str(profile.get("full_name", "")), country_code)
    return catalog


def resolve_country_code(
    country_text: str | None,
    catalog: dict[str, str],
    *,
    available_codes: set[str],
    default_code: str = DEFAULT_COUNTRY_CODE,
) -> tuple[str, bool, bool]:
    """
    Определяет код страны для выборки.

    :return: (country_code, used_default, user_country_missing_in_sample)
    """
    if not country_text:
        return default_code, True, False

    normalized = normalize_match_text(country_text)
    resolved = catalog.get(normalized)
    if resolved and resolved in available_codes:
        return resolved, False, False
    if resolved and resolved not in available_codes:
        return default_code, True, True
    return default_code, True, True
