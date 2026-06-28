# coding: utf-8
"""Форматирование исключений для логов и сообщений пользователю."""

from __future__ import annotations

import traceback
from typing import Any

ANALYTICS_FEATURE_LABELS: dict[str, str] = {
    "find_country": "Найти страну",
    "find_own_place": "Понять своё место в социуме",
    "country_plot": "График стран",
}


def analytics_feature_label(feature: str) -> str:
    return ANALYTICS_FEATURE_LABELS.get(feature, feature)


def describe_exception(exc: BaseException) -> dict[str, str]:
    exc_type = type(exc)
    module = exc_type.__module__
    error_name = exc_type.__qualname__
    if module in {"builtins", "__builtin__"}:
        error_type = error_name
    else:
        error_type = f"{module}.{error_name}"
    message = str(exc).strip()
    if not message:
        message = repr(exc)
    return {
        "module": module,
        "error_name": error_name,
        "error_type": error_type,
        "error_message": message,
    }


def format_traceback(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def analytics_error_event_parameters(feature: str, exc: BaseException) -> dict[str, Any]:
    return {
        "feature": feature,
        **describe_exception(exc),
        "traceback": format_traceback(exc),
    }
