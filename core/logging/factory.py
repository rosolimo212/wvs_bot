# coding: utf-8
"""
Фабрика логгера по настройкам app.logging_enabled.

При включённом логировании поднимает схему wvs при старте.
"""

from __future__ import annotations

from typing import Any

from core.db_schema import ensure_wvs_schema
from core.logging.base import EventLogger
from core.logging.noop import NoopLogger
from core.logging.postgres import PostgresLogger


def build_logger(config: dict[str, Any]) -> EventLogger:
    """
    Создаёт postgres-логгер или noop в зависимости от флага.

    :param config: полный конфиг из load_app_config
    :return: реализация EventLogger
    """
    if config["app"].get("logging_enabled"):
        logging_cfg = config["logging"]
        ensure_wvs_schema(logging_cfg)
        return PostgresLogger(logging_cfg)
    return NoopLogger()
