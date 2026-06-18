from __future__ import annotations

from core.learn_more import LEARN_MORE_COUNT, learn_more_answer_text, learn_more_question_buttons


def test_learn_more_faq_has_nine_items() -> None:
    assert len(learn_more_question_buttons()) == LEARN_MORE_COUNT


def test_learn_more_clusters_item_at_position_five() -> None:
    buttons = learn_more_question_buttons()
    assert buttons[4] == "А что это за кластеры стран?"
    assert "Кластер 0" in learn_more_answer_text(5)
