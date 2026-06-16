# coding: utf-8
"""Контракт хранилища ответов основной анкеты."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MainAnswerStore(ABC):
    """Чтение и запись ответов пользователя на основную анкету."""

    @abstractmethod
    def get_next_question_index(self, user_id: str, total_questions: int) -> int | None:
        """
        Индекс следующего вопроса (0-based).

        :return: None, если все вопросы уже отвечены.
        """

    @abstractmethod
    def is_complete(self, user_id: str, total_questions: int) -> bool:
        """True, если пользователь ответил на все вопросы основной анкеты."""

    @abstractmethod
    def save_answer(
        self,
        user_id: str,
        user_name: str,
        question: dict[str, Any],
        answer_text: str,
    ) -> None:
        """Сохраняет один ответ пользователя."""
