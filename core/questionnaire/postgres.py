# coding: utf-8
"""Postgres-хранилище ответов основной анкеты (wvs.user_answers)."""

from __future__ import annotations

from typing import Any

from core.db import postgres_connection
from core.questionnaire.base import MainAnswerStore


class PostgresMainAnswerStore(MainAnswerStore):
    def __init__(self, logging_config: dict[str, Any]) -> None:
        self._cfg = logging_config
        self._schema = logging_config["schema"]

    def _max_qv_number(self, user_id: str) -> int:
        table = f"{self._schema}.user_answers"
        with postgres_connection(self._cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT COALESCE(MAX(qv_number), 0)::int AS num
                    FROM {table}
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

    def save_answer(
        self,
        user_id: str,
        user_name: str,
        question: dict[str, Any],
        answer_text: str,
    ) -> None:
        table = f"{self._schema}.user_answers"
        qv_number = int(question["num"])
        with postgres_connection(self._cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {table}
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
