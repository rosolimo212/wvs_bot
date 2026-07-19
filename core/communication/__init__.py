# coding: utf-8
"""Исходящая коммуникация: дайджесты, позже — триггерные сообщения."""

from core.communication.daily_audience import (
    AudienceReport,
    ChannelMetrics,
    DailyAudienceRunResult,
    collect_audience_metrics,
    format_audience_report,
    run_daily_audience_report,
)

__all__ = [
    "AudienceReport",
    "ChannelMetrics",
    "DailyAudienceRunResult",
    "collect_audience_metrics",
    "format_audience_report",
    "run_daily_audience_report",
]
