# coding: utf-8
"""
Подключение к postgres.

Цель:
    Единые функции для SQLAlchemy engine и psycopg2-соединения.

Вход:
    Секция logging из config.yaml.

Выход:
    engine или connection для записи в схему wvs.

Риски:
    get_connection() возвращает «сырое» соединение — вызывающий обязан conn.close().
    Предпочтительно: with postgres_connection(...) as conn.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_engine(logging_config: dict[str, Any]) -> Engine:
    """Создаёт SQLAlchemy engine для pandas.to_sql."""
    url = (
        "postgresql://"
        f"{logging_config['user']}:{logging_config['password']}"
        f"@{logging_config['host']}:{logging_config['port']}"
        f"/{logging_config['database']}"
    )
    return create_engine(url)


def get_connection(logging_config: dict[str, Any]):
    """Открывает psycopg2-соединение для точечных SQL-запросов."""
    return psycopg2.connect(
        host=logging_config["host"],
        port=logging_config["port"],
        database=logging_config["database"],
        user=logging_config["user"],
        password=logging_config["password"],
    )


@contextmanager
def postgres_connection(
    logging_config: dict[str, Any],
) -> Generator[Any, None, None]:
    """Context manager: commit при успехе, rollback при ошибке, close в finally."""
    conn = get_connection(logging_config)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
