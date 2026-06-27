# coding: utf-8
"""Сравнение индексов пользователя с выборкой WVS и другими пользователями бота."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from core.analytics.country_lookup import (
    DEFAULT_COUNTRY_CODE,
    load_country_alias_catalog,
    resolve_country_code,
)
from core.analytics.indices import compute_indices_from_answers
from core.analytics.secondary_profile import SecondaryProfile, parse_secondary_profile
from core.analytics.sql import fetch_all_rows
from core.country_profiles import load_country_profiles

REQUIRED_MAIN_ANSWERS = 13
MIN_STRAT_SAMPLE = 30
MIN_BOT_GLOBAL_SAMPLE = 1
MIN_BOT_AGE_SAMPLE = 2
AGE_WINDOWS = (3, 5, 10)


@dataclass(frozen=True)
class UserPosition:
    rv: float
    sv: float
    rv_rank: int
    sv_rank: int


@dataclass(frozen=True)
class GenSampleRow:
    country_code: str
    rv: float
    sv: float
    age: int
    gender_code: int | None


@dataclass(frozen=True)
class BotUserRow:
    user_id: str
    country_code: str
    rv: float
    sv: float
    age: int | None
    gender_code: int | None


@dataclass(frozen=True)
class OwnPlaceContext:
    country_code: str
    country_name: str
    used_default_country: bool
    user_country_missing_in_sample: bool
    age_window: int | None
    age_sample_size: int | None
    age_sample_too_small: bool


@dataclass(frozen=True)
class BotComparisonResult:
    global_pos: UserPosition | None
    age_pos: UserPosition | None
    gender_age_pos: UserPosition | None
    other_users_count: int
    age_window: int | None
    age_sample_size: int | None
    age_sample_too_small: bool


@dataclass(frozen=True)
class OwnPlaceResult:
    global_pos: UserPosition
    context: OwnPlaceContext
    age_pos: UserPosition | None
    gender_age_pos: UserPosition | None
    bot: BotComparisonResult | None


def rank_percent(user_value: float, sample_values: list[float]) -> int:
    if not sample_values:
        return 0
    lower = sum(1 for value in sample_values if value < user_value)
    return int(round(lower / len(sample_values) * 100))


def _position_from_sample(
    user_rv: float,
    user_sv: float,
    rows: list[GenSampleRow] | list[BotUserRow],
) -> UserPosition | None:
    if not rows:
        return None
    rv_values = [row.rv for row in rows]
    sv_values = [row.sv for row in rows]
    return UserPosition(
        rv=user_rv,
        sv=user_sv,
        rv_rank=rank_percent(user_rv, rv_values),
        sv_rank=rank_percent(user_sv, sv_values),
    )


def _gender_to_code(gender: str | None) -> int | None:
    if not gender:
        return None
    normalized = gender.casefold()
    if normalized == "мужчина":
        return 1
    if normalized == "женщина":
        return 2
    return None


def _filter_age(rows: list[GenSampleRow], age: int, window: int) -> list[GenSampleRow]:
    return [row for row in rows if abs(row.age - age) <= window]


def _filter_bot_age(rows: list[BotUserRow], age: int, window: int) -> list[BotUserRow]:
    return [row for row in rows if row.age is not None and abs(row.age - age) <= window]


def _choose_age_rows(
    rows: list[GenSampleRow],
    age: int,
) -> tuple[int | None, list[GenSampleRow], bool]:
    for window in AGE_WINDOWS:
        filtered = _filter_age(rows, age, window)
        if len(filtered) >= MIN_STRAT_SAMPLE:
            return window, filtered, False
    last_window = AGE_WINDOWS[-1]
    filtered = _filter_age(rows, age, last_window)
    if not filtered:
        return last_window, [], True
    return last_window, filtered, len(filtered) < MIN_STRAT_SAMPLE


def _choose_bot_age_rows(
    rows: list[BotUserRow],
    age: int,
) -> tuple[int | None, list[BotUserRow], bool]:
    for window in AGE_WINDOWS:
        filtered = _filter_bot_age(rows, age, window)
        if len(filtered) >= MIN_BOT_AGE_SAMPLE:
            return window, filtered, False
    last_window = AGE_WINDOWS[-1]
    filtered = _filter_bot_age(rows, age, last_window)
    if not filtered:
        return last_window, [], True
    return last_window, filtered, len(filtered) < MIN_BOT_AGE_SAMPLE


def load_gen_sample_rows(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "wvs",
) -> list[GenSampleRow]:
    schema = reference_schema
    query = f"""
        SELECT
            "B_COUNTRY_ALPHA",
            "Q173" + "Q45" + "Q69" + "Q6" + "Q27" + "Q70" + "Q65" AS rv,
            "Q17" + "Q8" + "Q11" + "Q30" + "Q29" + "Q33" + "Q152" AS sv,
            "Q262",
            "Q260"
        FROM {schema}.gen_sample
        WHERE "Q262" IS NOT NULL
    """
    rows: list[GenSampleRow] = []
    for row in fetch_all_rows(query, logging_config):
        gender_raw = row[4]
        gender_code = int(gender_raw) if gender_raw is not None else None
        rows.append(
            GenSampleRow(
                country_code=str(row[0]).upper(),
                rv=float(row[1]),
                sv=float(row[2]),
                age=int(row[3]),
                gender_code=gender_code,
            )
        )
    return rows


def _resolve_bot_country_code(
    profile: SecondaryProfile,
    catalog: dict[str, str],
    available_codes: set[str],
) -> str:
    country_code, _, _ = resolve_country_code(
        profile.country_text,
        catalog,
        available_codes=available_codes,
        default_code=DEFAULT_COUNTRY_CODE,
    )
    if country_code not in available_codes:
        return DEFAULT_COUNTRY_CODE
    return country_code


def load_bot_user_rows(
    logging_config: dict[str, Any],
    *,
    exclude_user_id: str | None = None,
    reference_schema: str = "wvs",
    required_main_answers: int = REQUIRED_MAIN_ANSWERS,
) -> list[BotUserRow]:
    schema = logging_config["schema"]
    catalog = load_country_alias_catalog(logging_config, reference_schema=reference_schema)
    available_codes = set(catalog.values()) | {DEFAULT_COUNTRY_CODE}

    main_query = f"""
        SELECT user_id, qv_id, answer_text
        FROM {schema}.user_answers
        WHERE user_id IN (
            SELECT user_id
            FROM {schema}.user_answers
            GROUP BY user_id
            HAVING COUNT(DISTINCT qv_number) >= {required_main_answers}
        )
    """
    review_query = f"""
        SELECT user_id, qv_id, answer_text
        FROM {schema}.user_reviews
        WHERE user_id IN (
            SELECT user_id
            FROM {schema}.user_answers
            GROUP BY user_id
            HAVING COUNT(DISTINCT qv_number) >= {required_main_answers}
        )
    """

    main_by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for user_id, qv_id, answer_text in fetch_all_rows(main_query, logging_config):
        uid = str(user_id)
        if exclude_user_id and uid == exclude_user_id:
            continue
        main_by_user[uid].append(
            {"qv_id": str(qv_id), "answer_text": str(answer_text)}
        )

    reviews_by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for user_id, qv_id, answer_text in fetch_all_rows(review_query, logging_config):
        uid = str(user_id)
        if exclude_user_id and uid == exclude_user_id:
            continue
        reviews_by_user[uid].append(
            {"qv_id": str(qv_id), "answer_text": str(answer_text)}
        )

    rows: list[BotUserRow] = []
    for user_id, answers in main_by_user.items():
        indices = compute_indices_from_answers(answers)
        if indices is None:
            continue
        rv, sv = indices
        profile = parse_secondary_profile(reviews_by_user.get(user_id, []))
        country_code = _resolve_bot_country_code(profile, catalog, available_codes)
        rows.append(
            BotUserRow(
                user_id=user_id,
                country_code=country_code,
                rv=float(rv),
                sv=float(sv),
                age=profile.age,
                gender_code=_gender_to_code(profile.gender),
            )
        )
    return rows


def _compute_bot_comparison(
    *,
    user_rv: float,
    user_sv: float,
    profile: SecondaryProfile,
    country_code: str,
    bot_rows: list[BotUserRow],
) -> BotComparisonResult | None:
    country_rows = [row for row in bot_rows if row.country_code == country_code]
    if len(country_rows) < MIN_BOT_GLOBAL_SAMPLE:
        return None

    global_pos = _position_from_sample(user_rv, user_sv, country_rows)
    age_pos = None
    gender_age_pos = None
    age_window = None
    age_sample_size = None
    age_sample_too_small = False

    if profile.age is not None:
        age_window, age_rows, age_sample_too_small = _choose_bot_age_rows(
            country_rows,
            profile.age,
        )
        age_sample_size = len(age_rows)
        if age_rows and not age_sample_too_small:
            age_pos = _position_from_sample(user_rv, user_sv, age_rows)

        gender_code = _gender_to_code(profile.gender)
        if gender_code is not None and age_pos is not None and age_rows:
            gender_age_rows = [
                row for row in age_rows if row.gender_code == gender_code
            ]
            if len(gender_age_rows) >= MIN_BOT_AGE_SAMPLE:
                gender_age_pos = _position_from_sample(user_rv, user_sv, gender_age_rows)

    return BotComparisonResult(
        global_pos=global_pos,
        age_pos=age_pos,
        gender_age_pos=gender_age_pos,
        other_users_count=len(country_rows),
        age_window=age_window,
        age_sample_size=age_sample_size,
        age_sample_too_small=age_sample_too_small,
    )


def _country_display_name(country_code: str) -> str:
    profiles = load_country_profiles()
    profile = profiles.get(country_code.upper())
    if profile and profile.get("full_name"):
        return str(profile["full_name"])
    return country_code.upper()


def compute_own_place(
    *,
    user_rv: float,
    user_sv: float,
    profile: SecondaryProfile,
    logging_config: dict[str, Any],
    reference_schema: str = "wvs",
    exclude_user_id: str | None = None,
) -> OwnPlaceResult | None:
    sample_rows = load_gen_sample_rows(logging_config, reference_schema=reference_schema)
    if not sample_rows:
        return None

    available_codes = {row.country_code for row in sample_rows}
    catalog = load_country_alias_catalog(logging_config, reference_schema=reference_schema)
    country_code, used_default, missing_in_sample = resolve_country_code(
        profile.country_text,
        catalog,
        available_codes=available_codes,
        default_code=DEFAULT_COUNTRY_CODE,
    )

    country_rows = [row for row in sample_rows if row.country_code == country_code]
    if not country_rows:
        country_code = DEFAULT_COUNTRY_CODE
        used_default = True
        missing_in_sample = True
        country_rows = [row for row in sample_rows if row.country_code == country_code]
    if not country_rows:
        return None

    global_pos = _position_from_sample(user_rv, user_sv, country_rows)
    if global_pos is None:
        return None

    age_pos = None
    gender_age_pos = None
    age_window = None
    age_sample_size = None
    age_sample_too_small = False

    if profile.age is not None:
        age_window, age_rows, age_sample_too_small = _choose_age_rows(country_rows, profile.age)
        age_sample_size = len(age_rows)
        age_pos = _position_from_sample(user_rv, user_sv, age_rows)

        gender_code = _gender_to_code(profile.gender)
        if gender_code is not None and age_pos is not None:
            gender_age_rows = [
                row for row in age_rows if row.gender_code == gender_code
            ]
            if len(gender_age_rows) >= MIN_STRAT_SAMPLE:
                gender_age_pos = _position_from_sample(user_rv, user_sv, gender_age_rows)

    context = OwnPlaceContext(
        country_code=country_code,
        country_name=_country_display_name(country_code),
        used_default_country=used_default,
        user_country_missing_in_sample=missing_in_sample,
        age_window=age_window,
        age_sample_size=age_sample_size,
        age_sample_too_small=age_sample_too_small,
    )

    bot_rows = load_bot_user_rows(
        logging_config,
        exclude_user_id=exclude_user_id,
        reference_schema=reference_schema,
    )
    bot = _compute_bot_comparison(
        user_rv=user_rv,
        user_sv=user_sv,
        profile=profile,
        country_code=country_code,
        bot_rows=bot_rows,
    )

    return OwnPlaceResult(
        global_pos=global_pos,
        context=context,
        age_pos=age_pos,
        gender_age_pos=gender_age_pos,
        bot=bot,
    )
