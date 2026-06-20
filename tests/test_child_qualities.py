from __future__ import annotations

from core.analytics.child_qualities import (
    text_mentions_imagination,
    text_mentions_obedience,
)
from core.analytics.indices import answer_value, compute_indices_from_answers


def test_obedience_case_and_synonyms() -> None:
    assert text_mentions_obedience("Послушание")
    assert text_mentions_obedience("ПОСЛУШАНИЕ и дисциплина")
    assert text_mentions_obedience("obedience")
    assert text_mentions_obedience("исполнительность")


def test_obedience_typos() -> None:
    assert text_mentions_obedience("послушениe")
    assert text_mentions_obedience("poslushanie")


def test_obedience_negative() -> None:
    assert not text_mentions_obedience("Трудолюбие, честность")
    assert not text_mentions_obedience("дисциплина")


def test_imagination_case_and_synonyms() -> None:
    assert text_mentions_imagination("Воображение")
    assert text_mentions_imagination("IMAGINATION")
    assert text_mentions_imagination("фантазия, трудолюбие")
    assert text_mentions_imagination("креативность")
    assert text_mentions_imagination("творческое мышление")


def test_imagination_typos() -> None:
    assert text_mentions_imagination("ваображение")
    assert text_mentions_imagination("voobrazhenie")


def test_imagination_negative() -> None:
    assert not text_mentions_imagination("Трудолюбие, честность")
    assert not text_mentions_imagination("послушание")


def test_answer_value_q17_text() -> None:
    assert answer_value("Q17", "Трудолюбие") == 2
    assert answer_value("Q17", "Послушание и дисциплина") == 1
    assert answer_value("Q17", "poslushanie") == 1


def test_answer_value_q11_text() -> None:
    assert answer_value("Q11", "Трудолюбие") == 2
    assert answer_value("Q11", "Фантазия и смелость") == 1
    assert answer_value("Q11", "imagination") == 1


def test_compute_indices_derives_q11_from_q17_text() -> None:
    answers = [
        {"qv_id": "Q173", "answer_text": "1. Религиозный человек"},
        {"qv_id": "Q45", "answer_text": "1. Тогда будет лучше"},
        {"qv_id": "Q17", "answer_text": "воображение, трудолюбие"},
    ]
    rv, sv = compute_indices_from_answers(answers)
    assert rv == 3  # Q17=2 (нет послушания), Q11=1 (воображение из того же текста)
    assert sv == 2
