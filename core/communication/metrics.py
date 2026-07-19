# coding: utf-8
"""
Метрики аудитории для daily-отчёта.

Источник: Postgres-схема wvs (users, events, user_answers, user_reviews).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from core.db import postgres_connection

MSK = ZoneInfo("Europe/Moscow")

# Последний вопрос основной / дополнительной анкеты (см. questions.json).
PRIMARY_COMPLETE_QV_NUMBER = 13
SECONDARY_COMPLETE_QV_NUMBER = 14


@dataclass(frozen=True)
class ChannelMetrics:
    channel: str
    registered: int = 0
    primary_complete: int = 0
    secondary_complete: int = 0
    active_period: int = 0


@dataclass(frozen=True)
class AudienceReport:
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    by_channel: tuple[ChannelMetrics, ...]


def _as_msk(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=MSK)
    return moment.astimezone(MSK)


def _naive_local(moment: datetime) -> datetime:
    """TIMESTAMP в БД без tz — сравниваем как локальное MSK-время."""
    return _as_msk(moment).replace(tzinfo=None)


def _merge_counts(
    *groups: dict[str, int],
) -> dict[str, dict[str, int]]:
    keys: set[str] = set()
    for group in groups:
        keys.update(group)
    result: dict[str, dict[str, int]] = {}
    metric_names = ("registered", "primary_complete", "secondary_complete", "active_period")
    for channel in keys:
        result[channel] = {
            name: groups[idx].get(channel, 0) for idx, name in enumerate(metric_names)
        }
    return result


def _fetch_channel_counts(
    logging_config: dict[str, Any],
    query: str,
    params: tuple[Any, ...] | None = None,
) -> dict[str, int]:
    schema = logging_config["schema"]
    sql = query.format(schema=schema)
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
    return {str(channel): int(count) for channel, count in rows if channel is not None}


def collect_audience_metrics(
    logging_config: dict[str, Any],
    *,
    now: datetime | None = None,
    lookback: timedelta = timedelta(hours=24),
) -> AudienceReport:
    """
    Собирает метрики по каналам.

    - зарегистрированные / заполненные анкеты — за всё время;
    - активные — distinct user_id с ≥1 событием в events за [now-lookback, now).
    """
    end = _as_msk(now or datetime.now(timezone.utc))
    start = end - lookback
    period_start_db = _naive_local(start)
    period_end_db = _naive_local(end)

    registered = _fetch_channel_counts(
        logging_config,
        """
        SELECT registration_channel, COUNT(DISTINCT user_id)
        FROM {schema}.users
        GROUP BY registration_channel
        """,
    )
    primary = _fetch_channel_counts(
        logging_config,
        """
        SELECT u.registration_channel, COUNT(DISTINCT a.user_id)
        FROM {schema}.user_answers AS a
        JOIN {schema}.users AS u ON u.user_id = a.user_id
        WHERE a.qv_number = %s
        GROUP BY u.registration_channel
        """,
        (PRIMARY_COMPLETE_QV_NUMBER,),
    )
    secondary = _fetch_channel_counts(
        logging_config,
        """
        SELECT u.registration_channel, COUNT(DISTINCT r.user_id)
        FROM {schema}.user_reviews AS r
        JOIN {schema}.users AS u ON u.user_id = r.user_id
        WHERE r.qv_number = %s
        GROUP BY u.registration_channel
        """,
        (SECONDARY_COMPLETE_QV_NUMBER,),
    )
    active = _fetch_channel_counts(
        logging_config,
        """
        SELECT channel, COUNT(DISTINCT user_id)
        FROM {schema}.events
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY channel
        """,
        (period_start_db, period_end_db),
    )

    merged = _merge_counts(registered, primary, secondary, active)
    ordered_channels = sorted(merged.keys())
    by_channel = tuple(
        ChannelMetrics(
            channel=channel,
            registered=merged[channel]["registered"],
            primary_complete=merged[channel]["primary_complete"],
            secondary_complete=merged[channel]["secondary_complete"],
            active_period=merged[channel]["active_period"],
        )
        for channel in ordered_channels
    )
    return AudienceReport(
        generated_at=end,
        period_start=start,
        period_end=end,
        by_channel=by_channel,
    )
