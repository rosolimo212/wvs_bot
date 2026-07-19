# coding: utf-8
"""Журнал wvs.communications: id, идемпотентность, rate limit."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.db import postgres_connection

STATUS_SENT = "sent"
STATUS_FAILED = "failed"

DEFAULT_RATE_LIMIT = timedelta(hours=1)


def allocate_communication_id(logging_config: dict[str, Any]) -> int:
    schema = logging_config["schema"]
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT nextval('{schema}.communications_communication_id_seq')"
            )
            row = cur.fetchone()
    if row is None:
        raise RuntimeError("Не удалось выделить communication_id")
    return int(row[0])


def has_template_attempt(
    logging_config: dict[str, Any],
    *,
    user_id: str,
    template_id: str,
) -> bool:
    schema = logging_config["schema"]
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT 1
                FROM {schema}.communications
                WHERE user_id = %s AND template_id = %s
                LIMIT 1
                """,
                (user_id, template_id),
            )
            return cur.fetchone() is not None


def is_rate_limited(
    logging_config: dict[str, Any],
    *,
    user_id: str,
    now: datetime,
    window: timedelta = DEFAULT_RATE_LIMIT,
) -> bool:
    schema = logging_config["schema"]
    since = now - window
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT 1
                FROM {schema}.communications
                WHERE user_id = %s
                  AND sending_time >= %s
                LIMIT 1
                """,
                (user_id, since),
            )
            return cur.fetchone() is not None


def insert_communication(
    logging_config: dict[str, Any],
    *,
    communication_id: int,
    user_id: str,
    template_id: str,
    sending_time: datetime,
    status: str,
) -> None:
    schema = logging_config["schema"]
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {schema}.communications (
                    communication_id, user_id, template_id, sending_time, status
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (communication_id, user_id, template_id, sending_time, status),
            )
