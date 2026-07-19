from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from core.communication.channels import channel_report_label
from core.communication.daily_audience import run_daily_audience_report
from core.communication.formatters import format_audience_report
from core.communication.metrics import (
    AudienceReport,
    ChannelMetrics,
    collect_audience_metrics,
)

MSK = ZoneInfo("Europe/Moscow")


def test_channel_report_labels() -> None:
    assert channel_report_label("streamlit") == "браузер"
    assert channel_report_label("telegram") == "телега"
    assert channel_report_label("console") == "консоль"


def test_format_audience_report_contains_sections() -> None:
    report = AudienceReport(
        generated_at=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        period_start=datetime(2026, 7, 18, 11, 4, tzinfo=MSK),
        period_end=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        by_channel=(
            ChannelMetrics(
                channel="telegram",
                registered=10,
                primary_complete=4,
                secondary_complete=2,
                active_period=3,
            ),
            ChannelMetrics(
                channel="streamlit",
                registered=5,
                primary_complete=1,
                secondary_complete=0,
                active_period=1,
            ),
        ),
    )
    text = format_audience_report(report)
    assert "WVS · активность аудитории" in text
    assert "телега: 10" in text
    assert "браузер: 5" in text
    assert "Первичных анкет заполнено" in text
    assert "Активны за период" in text


def test_collect_audience_metrics_merges_channels() -> None:
    def fake_fetch(_cfg, query, params=None):
        q = " ".join(query.split())
        if "FROM {schema}.users" in q and "user_answers" not in q:
            return {"telegram": 2, "streamlit": 1}
        if "user_answers" in q:
            return {"telegram": 1}
        if "user_reviews" in q:
            return {"streamlit": 1}
        if "events" in q:
            return {"telegram": 1, "console": 1}
        raise AssertionError(q)

    with patch("core.communication.metrics._fetch_channel_counts", side_effect=fake_fetch):
        report = collect_audience_metrics(
            {"schema": "wvs"},
            now=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        )

    by = {row.channel: row for row in report.by_channel}
    assert set(by) == {"console", "streamlit", "telegram"}
    assert by["telegram"].registered == 2
    assert by["telegram"].primary_complete == 1
    assert by["telegram"].secondary_complete == 0
    assert by["telegram"].active_period == 1
    assert by["streamlit"].secondary_complete == 1
    assert by["console"].registered == 0
    assert by["console"].active_period == 1


@pytest.mark.asyncio
async def test_run_daily_report_dry_run_skips_send() -> None:
    report = AudienceReport(
        generated_at=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        period_start=datetime(2026, 7, 18, 11, 4, tzinfo=MSK),
        period_end=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        by_channel=(ChannelMetrics(channel="telegram", registered=1),),
    )
    with patch(
        "core.communication.daily_audience.collect_audience_metrics",
        return_value=report,
    ):
        with patch("core.communication.daily_audience.send_telegram_text") as send:
            text = await run_daily_audience_report(
                {"logging": {"schema": "wvs"}, "communication": {}},
                dry_run=True,
            )
    assert "телега: 1" in text
    send.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_report_requires_chat_id() -> None:
    report = AudienceReport(
        generated_at=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        period_start=datetime(2026, 7, 18, 11, 4, tzinfo=MSK),
        period_end=datetime(2026, 7, 19, 11, 4, tzinfo=MSK),
        by_channel=(),
    )
    with patch(
        "core.communication.daily_audience.collect_audience_metrics",
        return_value=report,
    ):
        with pytest.raises(ValueError, match="chat_id"):
            await run_daily_audience_report(
                {
                    "logging": {"schema": "wvs"},
                    "communication": {"daily_audience_report": {"enabled": True, "chat_id": ""}},
                    "telegram": {"token": "x"},
                },
                dry_run=False,
            )
