from __future__ import annotations

from core.questionnaire.loader import get_main_questions, load_questions, normalize_question_text


def test_normalize_question_text_replaces_slash_n() -> None:
    assert normalize_question_text("первая строка /nвторая") == "первая строка \nвторая"


def test_main_questions_normalize_text_on_load() -> None:
    data = load_questions("questions.json")
    questions = get_main_questions(data)
    q17 = next(q for q in questions if q["id"] == "Q17")
    assert "/n" not in q17["text"]
    assert "важными? \nПожалуйста" in q17["text"]
