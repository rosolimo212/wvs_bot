# coding: utf-8
"""Фабрика хранилища ответов основной анкеты."""

from __future__ import annotations

from typing import Any

from core.questionnaire.base import MainAnswerStore
from core.questionnaire.memory import MemoryMainAnswerStore
from core.questionnaire.postgres import PostgresMainAnswerStore


def build_main_answer_store(config: dict[str, Any]) -> MainAnswerStore:
    if config["app"].get("logging_enabled"):
        return PostgresMainAnswerStore(config["logging"])
    return MemoryMainAnswerStore()
