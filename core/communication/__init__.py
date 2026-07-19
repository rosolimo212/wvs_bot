# coding: utf-8
"""Исходящая коммуникация: дайджесты и рассылки."""

from core.communication.campaigns import (
    CommunicationRunResult,
    format_run_summary,
    run_communication,
)
from core.communication.daily_audience import (
    AudienceReport,
    ChannelMetrics,
    DailyAudienceRunResult,
    collect_audience_metrics,
    format_audience_report,
    run_daily_audience_report,
)
from core.communication.segments import KNOWN_SEGMENTS, TEST_USER_ID

__all__ = [
    "AudienceReport",
    "ChannelMetrics",
    "CommunicationRunResult",
    "DailyAudienceRunResult",
    "KNOWN_SEGMENTS",
    "TEST_USER_ID",
    "collect_audience_metrics",
    "format_audience_report",
    "format_run_summary",
    "run_communication",
    "run_daily_audience_report",
]
