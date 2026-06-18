from __future__ import annotations

from core.learn_more import LEARN_MORE_COUNT, learn_more_answer_text, learn_more_question_buttons


def test_learn_more_faq_has_eight_items() -> None:
    assert len(learn_more_question_buttons()) == LEARN_MORE_COUNT


def test_learn_more_first_answer() -> None:
    text = learn_more_answer_text(1)
    assert "социуме" in text.casefold()
