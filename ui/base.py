# coding: utf-8
"""
Общие вспомогательные функции для UI-клиентов.
"""

from __future__ import annotations

from typing import Any

from core.app import AppService
from core.logging.factory import build_logger
from core.questionnaire.factory import build_main_answer_store


def build_app_service(config: dict[str, Any]) -> AppService:
    logger = build_logger(config)
    answer_store = build_main_answer_store(config)
    return AppService(logger=logger, config=config, answer_store=answer_store)
