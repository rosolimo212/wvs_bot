# coding: utf-8
"""Форматирование текстов отчётов для Telegram."""

from __future__ import annotations

from core.communication.channels import channel_report_label
from core.communication.metrics import AudienceReport, ChannelMetrics


def _fmt_dt(moment) -> str:
    return moment.strftime("%d.%m.%Y %H:%M")


def _metric_lines(
    rows: tuple[ChannelMetrics, ...],
    attr: str,
) -> str:
    if not rows:
        return "  (нет данных)"
    parts = []
    for row in rows:
        label = channel_report_label(row.channel)
        value = getattr(row, attr)
        parts.append(f"  {label}: {value}")
    return "\n".join(parts)


def format_audience_report(report: AudienceReport) -> str:
    """Текст ежедневного дайджеста активности."""
    period = (
        f"{_fmt_dt(report.period_start)} — {_fmt_dt(report.period_end)} MSK"
    )
    rows = report.by_channel
    return "\n".join(
        [
            "WVS · активность аудитории",
            f"Период активности: {period}",
            "",
            "Зарегистрировано (всего):",
            _metric_lines(rows, "registered"),
            "",
            "Первичных анкет заполнено (всего):",
            _metric_lines(rows, "primary_complete"),
            "",
            "Вторичных анкет заполнено (всего):",
            _metric_lines(rows, "secondary_complete"),
            "",
            "Активны за период (≥1 событие):",
            _metric_lines(rows, "active_period"),
        ]
    )
