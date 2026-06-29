# coding: utf-8
"""Логирование в postgres (схема wvs)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from core.db import postgres_connection
from core.identity import make_user_id
from core.logging.base import EventLogger
from core.models import UserIdentity


class PostgresLogger(EventLogger):
    """Запись логов в postgres."""

    def __init__(self, logging_config: dict[str, Any]) -> None:
        self.logging_config = logging_config
        self.schema = logging_config["schema"]

    def _allocate_internal_user_id(self) -> int:
        table_name = f"{self.schema}.users"
        with postgres_connection(self.logging_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_get_serial_sequence(%s, %s)",
                    (table_name, "internal_user_id"),
                )
                seq_row = cur.fetchone()
                if seq_row is None or not seq_row[0]:
                    raise RuntimeError(
                        f"Не найден sequence для {self.schema}.users.internal_user_id"
                    )
                cur.execute("SELECT nextval(%s)", (seq_row[0],))
                row = cur.fetchone()

        if row is None:
            raise RuntimeError("postgres не вернул internal_user_id из sequence")

        return int(row[0])

    def _find_user(
        self, channel: str, external_user_id: str
    ) -> UserIdentity | None:
        """Ищет пользователя по channel + external_user_id."""
        table_name = f"{self.schema}.users"
        with postgres_connection(self.logging_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT user_id, internal_user_id, external_user_id
                    FROM {table_name}
                    WHERE registration_channel = %s AND external_user_id = %s
                    """,
                    (channel, external_user_id),
                )
                row = cur.fetchone()

        if row is None:
            return None

        return UserIdentity(
            user_id=str(row[0]),
            internal_user_id=int(row[1]),
            external_user_id=str(row[2]),
        )

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        table_name = f"{self.schema}.users"
        with postgres_connection(self.logging_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT user_name, registration_date
                    FROM {table_name}
                    WHERE user_id = %s
                    """,
                    (identity.user_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        return {
            "user_name": str(row[0] or ""),
            "registration_date": row[1],
        }

    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        existing = self._find_user(channel, external_user_id)
        if existing is not None:
            return existing

        user_id = make_user_id(channel, external_user_id)
        internal_user_id = self._allocate_internal_user_id()
        identity = UserIdentity(user_id, internal_user_id, external_user_id)

        now = datetime.now()
        self.upsert_user(
            identity,
            user_name="",
            registration_date=now,
            registration_channel=channel,
            last_active_at=now,
        )
        return identity

    def upsert_user(
        self,
        identity: UserIdentity,
        user_name: str,
        registration_date: datetime,
        registration_channel: str,
        last_active_at: datetime,
        is_paid: bool = False,
        is_trial: bool = False,
        is_active: bool = True,
    ) -> None:
        table_name = f"{self.schema}.users"
        query = f"""
            INSERT INTO {table_name} (
                user_id,
                internal_user_id,
                external_user_id,
                user_name,
                registration_date,
                registration_channel,
                last_active_at,
                is_paid,
                is_trial,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                user_name = EXCLUDED.user_name,
                registration_date = EXCLUDED.registration_date,
                registration_channel = EXCLUDED.registration_channel,
                last_active_at = EXCLUDED.last_active_at,
                is_paid = EXCLUDED.is_paid,
                is_trial = EXCLUDED.is_trial,
                is_active = EXCLUDED.is_active
        """

        with postgres_connection(self.logging_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        identity.user_id,
                        identity.internal_user_id,
                        identity.external_user_id,
                        user_name,
                        registration_date,
                        registration_channel,
                        last_active_at,
                        is_paid,
                        is_trial,
                        is_active,
                    ),
                )

    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        params_json = None
        if event_parameters is not None:
            params_json = json.dumps(event_parameters, ensure_ascii=False)

        table_name = f"{self.schema}.events"
        with postgres_connection(self.logging_config) as conn:
            with conn.cursor() as cur:
                if timestamp is None:
                    cur.execute(
                        f"""
                        INSERT INTO {table_name} (
                            timestamp,
                            user_id,
                            internal_user_id,
                            external_user_id,
                            event_name,
                            channel,
                            event_parameters
                        )
                        VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            identity.user_id,
                            identity.internal_user_id,
                            identity.external_user_id,
                            event_name,
                            channel,
                            params_json,
                        ),
                    )
                else:
                    cur.execute(
                        f"""
                        INSERT INTO {table_name} (
                            timestamp,
                            user_id,
                            internal_user_id,
                            external_user_id,
                            event_name,
                            channel,
                            event_parameters
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            timestamp,
                            identity.user_id,
                            identity.internal_user_id,
                            identity.external_user_id,
                            event_name,
                            channel,
                            params_json,
                        ),
                    )
