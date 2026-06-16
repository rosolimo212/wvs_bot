# coding: utf-8
"""
Контракт логирования.

Методы работают с тройкой идентификаторов:
    user_id (hash), internal_user_id, external_user_id.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from core.models import UserIdentity


class EventLogger(ABC):
    """Базовый интерфейс логгера событий и пользователей."""

    @abstractmethod
    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        """Находит или создаёт пользователя по channel + external_user_id."""

    @abstractmethod
    def upsert_user(
        self,
        identity: UserIdentity,
        user_name: str,
        registration_date: datetime,
        registration_channel: str,
        last_active_at: datetime,
        is_paid: bool = False,
        is_trial: bool = False,
        is_active: bool = True,
    ) -> None:
        """Создать или обновить запись пользователя по user_id (hash)."""

    @abstractmethod
    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Записать событие в events."""

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        """
        Профиль из users: user_name, registration_date.

        Пустой user_name означает, что регистрация ещё не завершена.
        """
        return None
