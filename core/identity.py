# coding: utf-8
"""
Идентификаторы пользователя.

user_id — sha256-хэш от конкатенации channel:external_user_id (ключ в БД).
internal_user_id — инкремент из postgres sequence.
external_user_id — id канала (telegram user id, session uuid и т.д.).
"""

from __future__ import annotations

import hashlib
import uuid


def make_user_id(channel: str, external_user_id: str) -> str:
    """
    Строит стабильный user_id (первичный ключ) из канала и внешнего id.

    :param channel: streamlit | telegram | console
    :param external_user_id: id сессии/пользователя в канале
    :return: hex-строка sha256
    """
    raw = f"{channel}:{external_user_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_external_user_id(channel: str) -> str:
    """
    Генерирует новый внешний id для каналов без встроенного user id.

    :param channel: streamlit | console
    :return: uuid4 string
    """
    _ = channel
    return str(uuid.uuid4())
