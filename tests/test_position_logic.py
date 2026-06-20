from __future__ import annotations

from core.analytics.country_lookup import build_country_alias_catalog, resolve_country_code
from core.analytics.indices import count_unknown_main_answers, should_warn_inaccurate_indices
from core.analytics.position import (
    GenSampleRow,
    _choose_age_rows,
    rank_percent,
)
from core.analytics.secondary_profile import parse_secondary_profile


def test_count_unknown_main_answers() -> None:
    answers = [
        {"qv_id": "Q173", "answer_text": "-1. Не знаю"},
        {"qv_id": "Q45", "answer_text": "1. Тогда будет лучше"},
    ]
    assert count_unknown_main_answers(answers) == 1


def test_should_warn_inaccurate_indices() -> None:
    assert not should_warn_inaccurate_indices(5)
    assert should_warn_inaccurate_indices(6)


def test_resolve_country_case_insensitive() -> None:
    catalog = build_country_alias_catalog(
        [
            ("RUS", "Russian Federation", "RU", "RUS"),
        ]
    )
    catalog["россия"] = "RUS"
    code, used_default, missing = resolve_country_code(
        "РОССИЯ",
        catalog,
        available_codes={"RUS", "USA"},
    )
    assert code == "RUS"
    assert used_default is False
    assert missing is False


def test_resolve_country_missing_in_sample_falls_back() -> None:
    catalog = build_country_alias_catalog([("USA", "United States", "US", "USA")])
    code, used_default, missing = resolve_country_code(
        "United States",
        catalog,
        available_codes={"RUS"},
    )
    assert code == "RUS"
    assert used_default is True
    assert missing is True


def test_rank_percent() -> None:
    assert rank_percent(5, [1, 2, 3, 4, 5]) == 80
    assert rank_percent(1, [1, 2, 3]) == 0


def test_choose_age_window_expands_until_enough() -> None:
    rows = [
        GenSampleRow("RUS", float(i % 20), 12.0, 38 + (i % 5), 1)
        for i in range(120)
    ]
    window, filtered, too_small = _choose_age_rows(rows, age=40)
    assert window == 3
    assert len(filtered) >= 30
    assert too_small is False


def test_choose_age_window_marks_small_sample() -> None:
    rows = [
        GenSampleRow("RUS", 10.0, 12.0, 40, 1),
        GenSampleRow("RUS", 11.0, 13.0, 41, 2),
    ]
    window, filtered, too_small = _choose_age_rows(rows, age=40)
    assert window == 10
    assert len(filtered) == 2
    assert too_small is True


def test_parse_secondary_profile() -> None:
    profile = parse_secondary_profile(
        [
            {"qv_id": "S01", "answer_text": "1990"},
            {"qv_id": "S02", "answer_text": "Германия"},
            {"qv_id": "S03", "answer_text": "Женщина"},
        ]
    )
    assert profile.birth_year == 1990
    assert profile.country_text == "Германия"
    assert profile.gender == "Женщина"
    assert profile.has_demographics
