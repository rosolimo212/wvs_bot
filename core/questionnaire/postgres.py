# coding: utf-8
"""Postgres-хранилище ответов анкеты."""

from __future__ import annotations

from typing import Any

from core.db import postgres_connection
from core.questionnaire.base import MainAnswerStore


class PostgresAnswerStore(MainAnswerStore):
    def __init__(self, logging_config: dict[str, Any], *, table: str) -> None:
        self._cfg = logging_config
        self._schema = logging_config["schema"]
        self._table = f"{self._schema}.{table}"

    def _max_qv_number(self, user_id: str) -> int:
        with postgres_connection(self._cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT COALESCE(MAX(qv_number), 0)::int AS num
                    FROM {self._table}
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
        if row is None:
            return 0
        return int(row[0])

    def get_next_question_index(self, user_id: str, total_questions: int) -> int | None:
        answered = self._max_qv_number(user_id)
        if answered >= total_questions:
            return None
        return answered

    def is_complete(self, user_id: str, total_questions: int) -> bool:
        return self.get_next_question_index(user_id, total_questions) is None

    def list_answers(self, user_id: str) -> list[dict[str, Any]]:
        with postgres_connection(self._cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT user_id, user_name, qv_id, qv_number, qv_text, answer_text
                    FROM {self._table}
                    WHERE user_id = %s
                    ORDER BY qv_number
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "user_id": row[0],
                "user_name": row[1],
                "qv_id": row[2],
                "qv_number": row[3],
                "qv_text": row[4],
                "answer_text": row[5],
            }
            for row in rows
        ]

    def save_answer(
        self,
        user_id: str,
        user_name: str,
        question: dict[str, Any],
        answer_text: str,
    ) -> None:
        qv_number = int(question["num"])
        with postgres_connection(self._cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._table}
                        (user_id, user_name, qv_id, qv_number, qv_text, answer_text)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, qv_number) DO UPDATE SET
                        user_name = EXCLUDED.user_name,
                        qv_id = EXCLUDED.qv_id,
                        qv_text = EXCLUDED.qv_text,
                        answer_text = EXCLUDED.answer_text,
                        insert_time = NOW()
                    """,
                    (
                        user_id,
                        user_name,
                        question["id"],
                        qv_number,
                        question["text"],
                        answer_text,
                    ),
                )


class PostgresMainAnswerStore(PostgresAnswerStore):
    def __init__(self, logging_config: dict[str, Any]) -> None:
        super().__init__(logging_config, table="user_answers")


class PostgresSecondaryAnswerStore(PostgresAnswerStore):
    def __init__(self, logging_config: dict[str, Any]) -> None:
        super().__init__(logging_config, table="user_reviews")
