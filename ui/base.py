# coding: utf-8
"""
Общие вспомогательные функции для UI-клиентов.

Цель:
    Создать AppService из конфига — одинаково для всех интерфейсов.
"""

from __future__ import annotations

from typing import Any

from core.app import AppService
from core.logging.factory import build_logger


def build_app_service(config: dict[str, Any]) -> AppService:
    logger = build_logger(config)
    return AppService(logger=logger, config=config)
