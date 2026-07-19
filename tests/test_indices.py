from __future__ import annotations

from core.analytics.indices import answer_value, compute_indices_from_answers


def test_answer_value_from_variant() -> None:
    assert answer_value("Q173", "1. Религиозный человек") == 1
    assert answer_value("Q173", "-1. Не знаю") is None


def test_answer_value_q17_text() -> None:
    assert answer_value("Q17", "Трудолюбие") == 2
    assert answer_value("Q17", "Послушание и дисциплина") == 1


def test_compute_indices_sums_groups() -> None:
    answers = [
        {"qv_id": "Q173", "answer_text": "1. Религиозный человек"},
        {"qv_id": "Q45", "answer_text": "1. Тогда будет лучше"},
        {"qv_id": "Q17", "answer_text": "Трудолюбие"},
    ]
    rv, sv = compute_indices_from_answers(answers)
    assert rv == 4  # Q17=2, Q11=2 (оба из текста «Трудолюбие»)
    assert sv == 2
