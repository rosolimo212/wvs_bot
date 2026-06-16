# coding: utf-8
"""In-memory хранилище ответов для тестов и режима без postgres."""

from __future__ import annotations

from typing import Any

from core.questionnaire.base import MainAnswerStore


class MemoryMainAnswerStore(MainAnswerStore):
    def __init__(self) -> None:
        self._answers: dict[str, list[dict[str, Any]]] = {}

    def _max_qv_number(self, user_id: str) -> int:
        rows = self._answers.get(user_id, [])
        if not rows:
            return 0
        return max(int(row["qv_number"]) for row in rows)

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
        rows = self._answers.setdefault(user_id, [])
        qv_number = int(question["num"])
        rows = [row for row in rows if int(row["qv_number"]) != qv_number]
        rows.append(
            {
                "user_id": user_id,
                "user_name": user_name,
                "qv_id": question["id"],
                "qv_number": qv_number,
                "qv_text": question["text"],
                "answer_text": answer_text,
            }
        )
        self._answers[user_id] = rows
