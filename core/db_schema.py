# coding: utf-8
"""
Инициализация схемы wvs при старте приложения.

Цель:
    Гарантировать наличие wvs.users и wvs.events без ручного запуска psql.

Вход:
    Секция logging из config.yaml (подключение к postgres).

Выход:
    Схема и таблицы созданы (IF NOT EXISTS).

Риски:
    Требует прав CREATE на базе communication.
    При недоступном postgres старт приложения завершится ошибкой.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.db import postgres_connection

SQL_FILES = (
    "sql/001_init.sql",
    "sql/003_unique_channel_external.sql",
)


def ensure_wvs_schema(logging_config: dict[str, Any]) -> None:
    """
    Выполняет SQL-скрипты инициализации схемы wvs.

    :param logging_config: секция logging из config.yaml
  """
    root = Path(__file__).resolve().parents[1]
    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            for rel_path in SQL_FILES:
                sql_path = root / rel_path
                sql_text = sql_path.read_text(encoding="utf-8")
                cur.execute(sql_text)
