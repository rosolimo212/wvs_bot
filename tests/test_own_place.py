from __future__ import annotations

from core.messages import message
from core.models import ACTION_MAIN_ANSWER, ACTION_OPTION_4
from tests.test_app import _register, _service


def test_main_questionary_complete_warns_many_unknown_answers() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-unknown")
    _register(service, identity)

    questions_by_id = {question["id"]: question for question in service._main_questions}

    response = None
    for question in service._main_questions:
        if question["id"] == "Q17":
            answer = "Трудолюбие"
            selected = ""
        else:
            unknown_variant = next(
                variant for variant in questions_by_id[question["id"]]["variants"] if variant.startswith("-1.")
            )
            answer = unknown_variant
            selected = answer
        response = service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {
                "user_name": "Роман",
                "selected": selected,
                "answer": answer,
            },
        )

    assert response is not None
    assert message("main_questionary_indices_inaccurate_warning", "streamlit") in response.text


def test_option_4_requires_secondary_questionary() -> None:
    service = _service()
    identity = service.logger.ensure_user("streamlit", "ext-own-place")
    _register(service, identity)

    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {
                "user_name": "Роман",
                "selected": variant,
                "answer": variant,
            },
        )

    response = service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_4,
        {"user_name": "Роман"},
    )
    assert message("find_own_place_need_secondary", "streamlit") in response.text
