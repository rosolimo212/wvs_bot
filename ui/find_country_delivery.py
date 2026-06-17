# coding: utf-8
"""
Отправка экрана «Найти страну»: текст, график, карточка, логирование таймингов.
"""

from __future__ import annotations

import time
from typing import Any

from core.country_profiles import format_country_profile
from core.models import Screen, UserIdentity
from ui.country_plot import export_country_plot_png


def append_country_profile_text(state: dict[str, Any], channel: str) -> str:
    """Добавляет карточку страны к last_text, если профиль есть."""
    meta = state.get("meta", {})
    country_code = str(meta.get("country_code", ""))
    profile_text = format_country_profile(country_code, channel)
    base = str(state.get("last_text", ""))
    if profile_text.strip():
        return f"{base}\n\n{profile_text}"
    return base


def deliver_find_country_telegram(
    service,
    identity: UserIdentity,
    state: dict[str, Any],
    config: dict[str, Any],
    channel: str = "telegram",
) -> dict[str, Any] | None:
    """
    Готовит данные для Telegram: текст, PNG графика, тайминги.

    :return: dict с keys text, png_bytes, timings или None если не FIND_COUNTRY
    """
    screen = state.get("screen", "")
    if screen != Screen.FIND_COUNTRY.value:
        state.pop("country_plot_delivered", None)
        return None

    meta = state.get("meta", {})
    if not meta.get("show_country_plot") or state.get("country_plot_delivered"):
        return None

    text = append_country_profile_text(state, channel)
    state["last_text"] = text
    state["country_plot_delivered"] = True

    logging_config = config.get("logging") if config.get("app", {}).get("logging_enabled") else None
    if logging_config is None:
        return {"text": text, "png_bytes": None, "timings": None}

    reference_schema = str(config.get("analytics", {}).get("reference_schema") or logging_config.get("schema", "wvs"))
    total_started = time.perf_counter()
    profile_started = time.perf_counter()
    _ = format_country_profile(str(meta.get("country_code", "")), channel)
    country_plot_loaded_ms = int((time.perf_counter() - profile_started) * 1000)

    png_bytes, timings = export_country_plot_png(
        float(meta["user_sv"]),
        float(meta["user_rv"]),
        logging_config,
        reference_schema=reference_schema,
    )
    total_ms = int((time.perf_counter() - total_started) * 1000)

    if timings is not None and png_bytes is not None:
        service.log_country_plot_loaded(
            identity,
            channel,
            sql_ms=timings.sql_ms,
            processing_ms=timings.processing_ms,
            render_ms=timings.render_ms,
            country_plot_loaded_ms=country_plot_loaded_ms,
            total_ms=total_ms,
        )

    return {"text": text, "png_bytes": png_bytes, "timings": timings}
