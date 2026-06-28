from __future__ import annotations

from core.error_reporting import (
    analytics_error_event_parameters,
    analytics_feature_label,
    describe_exception,
)


def test_describe_exception_name_error() -> None:
    try:
        raise NameError("_country_display_name is not defined")
    except NameError as exc:
        details = describe_exception(exc)
    assert details["module"] == "builtins"
    assert details["error_name"] == "NameError"
    assert "_country_display_name" in details["error_message"]


def test_analytics_error_event_parameters_includes_traceback() -> None:
    try:
        raise RuntimeError("db down")
    except RuntimeError as exc:
        params = analytics_error_event_parameters("find_own_place", exc)
    assert params["feature"] == "find_own_place"
    assert params["error_name"] == "RuntimeError"
    assert params["error_message"] == "db down"
    assert "RuntimeError: db down" in params["traceback"]


def test_analytics_feature_label() -> None:
    assert analytics_feature_label("find_country") == "Найти страну"
    assert analytics_feature_label("unknown") == "unknown"
