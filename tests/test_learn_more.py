from __future__ import annotations

from core.learn_more import LEARN_MORE_COUNT, learn_more_answer_text, learn_more_question_buttons
from core.models import ACTION_LEARN_MORE_ITEM, Screen


def test_learn_more_faq_has_nine_items() -> None:
    assert len(learn_more_question_buttons()) == LEARN_MORE_COUNT


def test_learn_more_clusters_item_at_position_five() -> None:
    buttons = learn_more_question_buttons()
    assert buttons[4] == "А что это за кластеры стран?"
    assert "Кластер 0" in learn_more_answer_text(5)


def test_learn_more_clusters_page_visit_logged() -> None:
    from core.messages import button
    from tests.test_logging_events import RecordingLogger, _service

    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-faq-clusters")
    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})
    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "text": button("menu_option_learn_more", "streamlit"),
            "screen": Screen.MAIN_MENU.value,
            "user_name": "Роман",
        },
    )

    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_LEARN_MORE_ITEM,
        {
            "screen": Screen.LEARN_MORE.value,
            "user_name": "Роман",
            "learn_more_item": 5,
        },
    )
    assert "Кластер 0" in response.text
    assert logger.events[-1] == "faq_page_visit"
    assert logger.event_parameters[-1] == {
        "screen_name": "А что это за кластеры стран?",
        "learn_more_item": 5,
        "faq_slug": "country_clusters",
    }
