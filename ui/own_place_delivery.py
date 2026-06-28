# coding: utf-8
"""Отправка гистограмм «Понять своё место» в Telegram."""

from __future__ import annotations

from typing import Any

from core.models import Screen, UserIdentity
from ui.own_place_plot import export_index_histogram_png


def deliver_own_place_telegram(
    state: dict[str, Any],
    channel: str = "telegram",
) -> dict[str, Any] | None:
    """
    Готовит текст и PNG-гистограммы для Telegram.

    :return: dict с keys text, png_list или None
    """
    screen = state.get("screen", "")
    if screen != Screen.FIND_OWN_PLACE.value:
        state.pop("own_place_charts_delivered", None)
        return None

    meta = state.get("meta", {})
    if not meta.get("show_own_place_charts") or state.get("own_place_charts_delivered"):
        return None

    charts = meta.get("own_place_charts") or []
    png_list: list[tuple[bytes, str]] = []
    for index, chart in enumerate(charts):
        png_bytes = export_index_histogram_png(
            list(chart["peer_values"]),
            float(chart["user_value"]),
            title=str(chart["title"]),
            x_label=str(chart["x_label"]),
        )
        if png_bytes:
            kind = str(chart.get("kind", index))
            png_list.append((png_bytes, f"own_place_{kind}.png"))

    state["own_place_charts_delivered"] = True
    return {
        "text": str(state.get("last_text", "")),
        "png_list": png_list,
    }
