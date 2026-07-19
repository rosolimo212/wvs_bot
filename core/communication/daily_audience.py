# coding: utf-8
"""Ежедневный отчёт активности аудитории."""

from __future__ import annotations

from typing import Any

from core.communication.formatters import format_audience_report
from core.communication.metrics import (
    AudienceReport,
    ChannelMetrics,
    collect_audience_metrics,
)
from core.communication.telegram_delivery import send_telegram_text

__all__ = [
    "AudienceReport",
    "ChannelMetrics",
    "collect_audience_metrics",
    "format_audience_report",
    "run_daily_audience_report",
]


def _report_config(config: dict[str, Any]) -> dict[str, Any]:
    communication = config.get("communication") or {}
    if not isinstance(communication, dict):
        return {}
    section = communication.get("daily_audience_report") or {}
    return section if isinstance(section, dict) else {}


async def run_daily_audience_report(
    config: dict[str, Any],
    *,
    dry_run: bool = False,
    chat_id: str | int | None = None,
) -> str:
    """
    Собирает метрики, форматирует текст, при необходимости шлёт в Telegram.

    :return: текст отчёта (всегда, даже при dry_run / отправке).
    """
    report_cfg = _report_config(config)
    if not dry_run and report_cfg.get("enabled") is False:
        raise RuntimeError("daily_audience_report выключен в config (enabled: false)")

    report = collect_audience_metrics(config["logging"])
    text = format_audience_report(report)

    if dry_run:
        return text

    resolved_chat_id = chat_id if chat_id is not None else report_cfg.get("chat_id")
    if resolved_chat_id is None or str(resolved_chat_id).strip() == "":
        raise ValueError(
            "Не задан chat_id. Укажите communication.daily_audience_report.chat_id "
            "в config.yaml или передайте --chat-id."
        )

    await send_telegram_text(config, chat_id=resolved_chat_id, text=text)
    return text
