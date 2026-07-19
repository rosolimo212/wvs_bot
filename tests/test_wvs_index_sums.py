from __future__ import annotations

from core.analytics.indices import (
    compute_indices_from_answers,
    count_unknown_main_answers,
    should_warn_inaccurate_indices,
)
from core.analytics.wvs_index_sums import (
    aggregate_country_means,
    compute_rv_sv_from_codes,
    is_valid_wvs_code,
)


def test_is_valid_wvs_code() -> None:
    assert is_valid_wvs_code(2) is True
    assert is_valid_wvs_code(-1) is False
    assert is_valid_wvs_code(0) is False
    assert is_valid_wvs_code(None) is False


def test_compute_rv_sv_skips_missing_codes() -> None:
    codes = {
        "Q173": 2,
        "Q45": -1,
        "Q69": 2,
        "Q6": 2,
        "Q27": 2,
        "Q70": 2,
        "Q65": 2,
        "Q17": 1,
        "Q8": 2,
        "Q11": 2,
        "Q30": 2,
        "Q29": 2,
        "Q33": 2,
        "Q152": 2,
    }
    rv, sv = compute_rv_sv_from_codes(codes)
    assert rv == 13  # 7 items × mostly 2, Q17=1 → 1+2*6=13
    assert sv == 12  # 6 valid SV items × 2


def test_compute_rv_sv_all_missing_returns_none() -> None:
    codes = {name: -1 for name in (
        "Q173", "Q45", "Q69", "Q6", "Q27", "Q70", "Q65",
        "Q17", "Q8", "Q11", "Q30", "Q29", "Q33", "Q152",
    )}
    assert compute_rv_sv_from_codes(codes) is None


def test_aggregate_country_means() -> None:
    means = aggregate_country_means([("RUS", 10, 12), ("RUS", 14, 16), ("USA", 20, 22)])
    assert means["RUS"] == (12.0, 14.0)
    assert means["USA"] == (20.0, 22.0)


def test_user_indices_skip_unknown() -> None:
    answers = [
        {"qv_id": "Q173", "answer_text": "-1. Не знаю"},
        {"qv_id": "Q45", "answer_text": "1. Тогда будет лучше"},
        {"qv_id": "Q69", "answer_text": "1. Согласен"},
        {"qv_id": "Q6", "answer_text": "1. Согласен"},
        {"qv_id": "Q27", "answer_text": "1. Согласен"},
        {"qv_id": "Q70", "answer_text": "1. Согласен"},
        {"qv_id": "Q65", "answer_text": "1. Согласен"},
        {"qv_id": "Q17", "answer_text": "Трудолюбие"},
    ]
    assert count_unknown_main_answers(answers) == 1
    rv, sv = compute_indices_from_answers(answers)
    assert sv == 6  # six ones, Q173 skipped
    assert rv == 4  # Q17=2, Q11=2 from same text


def test_should_warn_at_five_unknown() -> None:
    assert should_warn_inaccurate_indices(4) is False
    assert should_warn_inaccurate_indices(5) is True
