# coding: utf-8
"""Фабрика хранилищ ответов анкет."""

from __future__ import annotations

from typing import Any

from core.questionnaire.base import MainAnswerStore
from core.questionnaire.memory import MemoryMainAnswerStore, MemorySecondaryAnswerStore
from core.questionnaire.postgres import PostgresMainAnswerStore, PostgresSecondaryAnswerStore


def build_main_answer_store(config: dict[str, Any]) -> MainAnswerStore:
    if config["app"].get("logging_enabled"):
        return PostgresMainAnswerStore(config["logging"])
    return MemoryMainAnswerStore()


def build_secondary_answer_store(config: dict[str, Any]) -> MainAnswerStore:
    if config["app"].get("logging_enabled"):
        return PostgresSecondaryAnswerStore(config["logging"])
    return MemorySecondaryAnswerStore()
