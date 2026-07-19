# coding: utf-8
"""
Ежедневный отчёт активности аудитории.

Без --force/--dry-run отправка только в минуту send_at (timezone из config)
и не чаще одного раза в календарные сутки (маркер .cache/).
Запуск: scripts/send_daily_audience_report.py; на проде — systemd timer каждую минуту.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.communication.formatters import format_audience_report
from core.communication.metrics import (
    AudienceReport,
    ChannelMetrics,
    collect_audience_metrics,
)
from core.communication.schedule import (
    already_sent_today,
    default_sent_marker_path,
    is_send_at_now,
    resolve_timezone,
    write_sent_date,
)
from core.communication.telegram_delivery import send_telegram_text

__all__ = [
    "AudienceReport",
    "ChannelMetrics",
    "DailyAudienceRunResult",
    "collect_audience_metrics",
    "format_audience_report",
    "run_daily_audience_report",
]


@dataclass(frozen=True)
class DailyAudienceRunResult:
    text: str
    sent: bool
    skipped_reason: str | None = None


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
    force: bool = False,
    chat_id: str | int | None = None,
    now: datetime | None = None,
    sent_marker_path: Path | None = None,
) -> DailyAudienceRunResult:
    """
    Собирает метрики и при необходимости шлёт в Telegram.

    Без force/dry_run отправляет только в минуту send_at (timezone из конфига)
    и не чаще одного раза в календарные сутки.
    """
    report_cfg = _report_config(config)
    if not dry_run and not force and report_cfg.get("enabled") is False:
        return DailyAudienceRunResult(
            text="",
            sent=False,
            skipped_reason="disabled",
        )

    timezone = str(report_cfg.get("timezone") or "Europe/Moscow")
    send_at = str(report_cfg.get("send_at") or "11:04")
    marker = sent_marker_path or default_sent_marker_path()

    if not dry_run and not force:
        if not is_send_at_now(send_at=send_at, timezone=timezone, now=now):
            return DailyAudienceRunResult(
                text="",
                sent=False,
                skipped_reason=f"not_send_at ({send_at} {timezone})",
            )
        if already_sent_today(marker, timezone=timezone, now=now):
            return DailyAudienceRunResult(
                text="",
                sent=False,
                skipped_reason="already_sent_today",
            )

    report = collect_audience_metrics(config["logging"], now=now)
    text = format_audience_report(report)

    if dry_run:
        return DailyAudienceRunResult(text=text, sent=False, skipped_reason="dry_run")

    resolved_chat_id = chat_id if chat_id is not None else report_cfg.get("chat_id")
    if resolved_chat_id is None or str(resolved_chat_id).strip() == "":
        raise ValueError(
            "Не задан chat_id. Укажите communication.daily_audience_report.chat_id "
            "в config.yaml или передайте --chat-id."
        )

    await send_telegram_text(config, chat_id=resolved_chat_id, text=text)
    tz = resolve_timezone(timezone)
    moment = now.astimezone(tz) if now is not None else datetime.now(tz)
    write_sent_date(marker, moment.date())
    return DailyAudienceRunResult(text=text, sent=True)
