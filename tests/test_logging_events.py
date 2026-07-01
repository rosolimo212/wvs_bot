from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from core.analytics.country import NearestCountry
from core.app import AppService
from core.logging.noop import NoopLogger
from core.messages import back_to_menu_button, button, message
from core.models import ACTION_MAIN_ANSWER, ACTION_OPTION_2, ACTION_OPTION_3, ACTION_OPTION_4, Screen
from core.questionnaire.memory import MemoryMainAnswerStore, MemorySecondaryAnswerStore


class RecordingLogger(NoopLogger):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []
        self.event_parameters: list[dict] = []

    def log_event(self, identity, event_name, channel, event_parameters=None, timestamp=None):
        self.events.append(event_name)
        self.event_parameters.append(event_parameters or {})


def _service(logger: RecordingLogger) -> AppService:
    return AppService(
        logger,
        {
            "app": {"interface": "streamlit", "logging_enabled": False},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
    )


def test_back_to_menu_logs_click_then_visit() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-back")

    service.handle_action(
        identity,
        "streamlit",
        "name_entered",
        {"text": "Роман"},
    )
    service.handle_action(
        identity,
        "streamlit",
        ACTION_OPTION_2,
        {"user_name": "Роман"},
    )
    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "user_name": "Роман",
            "text": back_to_menu_button("streamlit"),
            "screen": "secondary_questionary",
        },
    )

    assert logger.events[-2:] == ["main_menu_click", "main_menu_visit"]
    assert logger.event_parameters[-2]["screen"] == "secondary_questionary"


def test_main_questionary_logs_question_and_answer() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-q")

    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})
    service.handle_action(identity, "streamlit", "option_1", {"user_name": "Роман"})
    assert "main_questionary_start" in logger.events
    assert "question_show" in logger.events

    first_variant = service._main_questions[0]["variants"][0]
    service.handle_action(
        identity,
        "streamlit",
        "main_answer",
        {
            "user_name": "Роман",
            "selected": first_variant,
            "answer": first_variant,
        },
    )
    assert "answer_sent" in logger.events
    answer_events = [
        params
        for name, params in zip(logger.events, logger.event_parameters, strict=False)
        if name == "answer_sent"
    ]
    assert answer_events[-1]["answer"] == first_variant
    assert answer_events[-1]["questionary"] == "main"
    assert answer_events[-1]["qv_text"]


def test_returning_user_does_not_log_start_screen_visit() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-return")
    service.logger.upsert_user(
        identity=identity,
        user_name="Роман",
        registration_date=datetime.now(),
        registration_channel="streamlit",
        last_active_at=datetime.now(),
    )

    service.handle_start(identity, "streamlit")

    assert "start_screen_visit" not in logger.events
    assert logger.events[-1] == "main_menu_visit"


def test_country_plot_loaded_logs_timings() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-plot")

    service.log_country_plot_loaded(
        identity,
        "streamlit",
        sql_ms=10,
        processing_ms=80,
        render_ms=20,
        country_plot_loaded_ms=5,
        total_ms=115,
    )

    assert logger.events[-1] == "country_plot_loaded"
    assert logger.event_parameters[-1] == {
        "sql_ms": 10,
        "processing_ms": 80,
        "render_ms": 20,
        "country_plot_loaded_ms": 5,
        "total_ms": 115,
    }


def test_find_country_start_logs_answer_text() -> None:
    logger = RecordingLogger()
    service = AppService(
        logger,
        {
            "app": {"interface": "streamlit", "logging_enabled": True},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
            "analytics": {"reference_schema": "wvs"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
    )
    identity = logger.ensure_user("streamlit", "ext-find-country")

    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})
    payload = {"user_name": "Роман"}

    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {**payload, "selected": variant, "answer": variant},
        )

    nearest = NearestCountry(
        rv=10.0,
        sv=12.0,
        country_code="RUS",
        country_rv=9.5,
        country_sv=11.5,
    )
    with patch("core.app.find_nearest_country", return_value=nearest) as mock_country:
        response = service.handle_action(identity, "streamlit", ACTION_OPTION_3, payload)

    mock_country.assert_called_once()
    call_args, call_kwargs = mock_country.call_args
    assert call_args[0] is service.answer_store
    assert call_args[1] == identity.user_id
    assert call_args[2] == service.config["logging"]
    assert call_kwargs["reference_schema"] == "wvs"

    assert "find_counry_start" in logger.events
    idx = len(logger.events) - 1 - logger.events[::-1].index("find_counry_start")
    assert logger.event_parameters[idx]["answer"] == response.text
    assert "RUS" in logger.event_parameters[idx]["answer"]


def test_find_country_exception_logs_analytics_error() -> None:
    logger = RecordingLogger()
    service = AppService(
        logger,
        {
            "app": {"interface": "streamlit", "logging_enabled": True},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
            "analytics": {"reference_schema": "wvs"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
    )
    identity = logger.ensure_user("streamlit", "ext-find-country-error")
    payload = {"user_name": "Роман"}

    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})
    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {**payload, "selected": variant, "answer": variant},
        )

    with patch("core.app.find_nearest_country", side_effect=RuntimeError("db timeout")):
        response = service.handle_action(identity, "streamlit", ACTION_OPTION_3, payload)

    assert "analytics_error" in logger.events
    error_idx = logger.events.index("analytics_error")
    assert logger.event_parameters[error_idx]["feature"] == "find_country"
    assert logger.event_parameters[error_idx]["error_name"] == "RuntimeError"
    assert "db timeout" in logger.event_parameters[error_idx]["error_message"]
    assert "RuntimeError: db timeout" in logger.event_parameters[error_idx]["traceback"]
    assert message("analytics_error", "streamlit", feature="Найти страну", module="builtins", error_name="RuntimeError", error_message="db timeout") in response.text
    assert message("analytics_no_data", "streamlit") not in response.text


def test_find_own_place_exception_logs_analytics_error() -> None:
    logger = RecordingLogger()
    service = AppService(
        logger,
        {
            "app": {"interface": "streamlit", "logging_enabled": True},
            "logging": {"schema": "wvs"},
            "telegram": {"token": ""},
            "paths": {"questions_file": "questions.json"},
            "analytics": {"reference_schema": "wvs"},
        },
        answer_store=MemoryMainAnswerStore(),
        secondary_answer_store=MemorySecondaryAnswerStore(),
    )
    identity = logger.ensure_user("streamlit", "ext-own-place-error")
    payload = {"user_name": "Роман"}

    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})
    for question in service._main_questions:
        variant = question["variants"][0]
        service.handle_action(
            identity,
            "streamlit",
            ACTION_MAIN_ANSWER,
            {**payload, "selected": variant, "answer": variant},
        )

    with (
        patch.object(service, "is_secondary_questionary_complete", return_value=True),
        patch("core.app.compute_own_place", side_effect=NameError("_country_display_name")),
    ):
        response = service.handle_action(identity, "streamlit", ACTION_OPTION_4, payload)

    assert "analytics_error" in logger.events
    error_idx = logger.events.index("analytics_error")
    assert logger.event_parameters[error_idx]["feature"] == "find_own_place"
    assert logger.event_parameters[error_idx]["error_name"] == "NameError"
    assert "_country_display_name" in response.text
    assert message("analytics_no_data", "streamlit") not in response.text


def test_faq_menu_and_page_visit_logged() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-faq")
    service.handle_action(identity, "streamlit", "name_entered", {"text": "Роман"})

    hub = service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "text": button("menu_option_learn_more", "streamlit"),
            "screen": Screen.MAIN_MENU.value,
            "user_name": "Роман",
        },
    )
    assert hub.screen == Screen.LEARN_MORE
    assert hub.buttons[0] == back_to_menu_button("streamlit")
    assert logger.events[-1] == "faq_menu_visit"
    assert logger.event_parameters[-1] == {}

    first_question = hub.buttons[1]
    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "text": first_question,
            "screen": Screen.LEARN_MORE.value,
            "user_name": "Роман",
        },
    )
    assert logger.events[-1] == "faq_page_visit"
    assert logger.event_parameters[-1] == {
        "screen_name": first_question,
        "learn_more_item": 1,
        "faq_slug": "what_do_i_get",
    }

    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "text": button("back_to_learn_more", "streamlit"),
            "screen": Screen.LEARN_MORE_ANSWER.value,
            "user_name": "Роман",
            "learn_more_item": 1,
        },
    )
    assert logger.events[-1] == "faq_menu_visit"


def test_faq_hub_back_to_main_menu_logged() -> None:
    logger = RecordingLogger()
    service = _service(logger)
    identity = logger.ensure_user("streamlit", "ext-faq-menu")
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

    service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            "text": back_to_menu_button("streamlit"),
            "screen": Screen.LEARN_MORE.value,
            "user_name": "Роман",
        },
    )

    assert logger.events[-2:] == ["main_menu_click", "main_menu_visit"]
    assert logger.event_parameters[-2]["screen"] == Screen.LEARN_MORE.value
