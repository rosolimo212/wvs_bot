# coding: utf-8
"""
Сегменты получателей исходящих коммуникаций.

test — один получатель: chat_id из communication.daily_audience_report.
Остальные — только registration_channel = telegram.
Заполненность анкет: qv_number=13 (user_answers), qv_number=14 (user_reviews).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.db import postgres_connection

PRIMARY_COMPLETE_QV_NUMBER = 13
SECONDARY_COMPLETE_QV_NUMBER = 14

TEST_USER_ID = "system:stats_chat"
TEST_USER_NAME = "team"

SEGMENT_TEST = "test"
SEGMENT_ALL_USERS = "all_users"
SEGMENT_PRIMARY_COMPLETE = "primary_complete"
SEGMENT_BOTH_COMPLETE = "both_complete"

KNOWN_SEGMENTS = (
    SEGMENT_TEST,
    SEGMENT_ALL_USERS,
    SEGMENT_PRIMARY_COMPLETE,
    SEGMENT_BOTH_COMPLETE,
)


@dataclass(frozen=True)
class CommunicationRecipient:
    user_id: str
    external_user_id: str
    user_name: str
    registration_channel: str


def _stats_chat_id(config: dict[str, Any]) -> str:
    communication = config.get("communication") or {}
    report = communication.get("daily_audience_report") or {}
    chat_id = str(report.get("chat_id") or "").strip()
    if not chat_id:
        raise ValueError(
            "Для сегмента test нужен communication.daily_audience_report.chat_id в config.yaml"
        )
    return chat_id


def _fetch_recipients(
    logging_config: dict[str, Any],
    query: str,
    params: tuple[Any, ...] = (),
) -> list[CommunicationRecipient]:
    schema = logging_config["schema"]
    sql = query.format(schema=schema)
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [
        CommunicationRecipient(
            user_id=str(user_id),
            external_user_id=str(external_user_id),
            user_name=str(user_name or ""),
            registration_channel=str(registration_channel),
        )
        for user_id, external_user_id, user_name, registration_channel in rows
    ]


def resolve_segment_recipients(
    config: dict[str, Any],
    segment: str,
) -> list[CommunicationRecipient]:
    """
    Возвращает получателей сегмента.

    Пользовательские сегменты — только registration_channel = telegram.
    """
    key = segment.strip()
    if key not in KNOWN_SEGMENTS:
        known = ", ".join(KNOWN_SEGMENTS)
        raise ValueError(f"Неизвестный сегмент {segment!r}. Доступны: {known}")

    if key == SEGMENT_TEST:
        chat_id = _stats_chat_id(config)
        return [
            CommunicationRecipient(
                user_id=TEST_USER_ID,
                external_user_id=chat_id,
                user_name=TEST_USER_NAME,
                registration_channel="telegram",
            )
        ]

    logging_config = config["logging"]
    if key == SEGMENT_ALL_USERS:
        return _fetch_recipients(
            logging_config,
            """
            SELECT user_id, external_user_id, user_name, registration_channel
            FROM {schema}.users
            WHERE registration_channel = 'telegram'
            ORDER BY internal_user_id
            """,
        )
    if key == SEGMENT_PRIMARY_COMPLETE:
        return _fetch_recipients(
            logging_config,
            """
            SELECT u.user_id, u.external_user_id, u.user_name, u.registration_channel
            FROM {schema}.users AS u
            WHERE u.registration_channel = 'telegram'
              AND EXISTS (
                  SELECT 1
                  FROM {schema}.user_answers AS a
                  WHERE a.user_id = u.user_id
                    AND a.qv_number = %s
              )
            ORDER BY u.internal_user_id
            """,
            (PRIMARY_COMPLETE_QV_NUMBER,),
        )
    # both_complete
    return _fetch_recipients(
        logging_config,
        """
        SELECT u.user_id, u.external_user_id, u.user_name, u.registration_channel
        FROM {schema}.users AS u
        WHERE u.registration_channel = 'telegram'
          AND EXISTS (
              SELECT 1
              FROM {schema}.user_answers AS a
              WHERE a.user_id = u.user_id
                AND a.qv_number = %s
          )
          AND EXISTS (
              SELECT 1
              FROM {schema}.user_reviews AS r
              WHERE r.user_id = u.user_id
                AND r.qv_number = %s
          )
        ORDER BY u.internal_user_id
        """,
        (PRIMARY_COMPLETE_QV_NUMBER, SECONDARY_COMPLETE_QV_NUMBER),
    )
