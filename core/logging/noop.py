# coding: utf-8
"""Логгер-заглушка при выключенном postgres."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.identity import make_user_id
from core.logging.base import EventLogger
from core.models import UserIdentity

DEFAULT_COUNTER_PATH = Path("data/user_counter.json")


class NoopLogger(EventLogger):
    """Логирование отключено; internal_user_id — локальный json-счётчик."""

    def __init__(self, counter_path: str | Path = DEFAULT_COUNTER_PATH) -> None:
        self.counter_path = Path(counter_path)
        self.counter_path.parent.mkdir(parents=True, exist_ok=True)
        self._known_users: dict[str, UserIdentity] = {}
        self._by_external: dict[tuple[str, str], UserIdentity] = {}
        self._profiles: dict[str, dict[str, Any]] = {}

    def _read_counter(self) -> int:
        if not self.counter_path.exists():
            return 0
        with self.counter_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("last_internal_user_id", 0))

    def _write_counter(self, value: int) -> None:
        with self.counter_path.open("w", encoding="utf-8") as f:
            json.dump({"last_internal_user_id": value}, f, ensure_ascii=False, indent=2)

    def _allocate_internal_user_id(self) -> int:
        current = self._read_counter()
        new_id = current + 1
        self._write_counter(new_id)
        return new_id

    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        key = (channel, external_user_id)
        if key in self._by_external:
            return self._by_external[key]

        user_id = make_user_id(channel, external_user_id)
        if user_id in self._known_users:
            identity = self._known_users[user_id]
            self._by_external[key] = identity
            return identity

        internal_user_id = self._allocate_internal_user_id()
        identity = UserIdentity(
            user_id=user_id,
            internal_user_id=internal_user_id,
            external_user_id=external_user_id,
        )
        self._known_users[user_id] = identity
        self._by_external[key] = identity
        return identity

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
        self._profiles[identity.user_id] = {
            "user_name": user_name,
            "registration_date": registration_date,
            "registration_channel": registration_channel,
            "last_active_at": last_active_at,
            "is_paid": is_paid,
            "is_trial": is_trial,
            "is_active": is_active,
        }

    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        _ = (identity, event_name, channel, event_parameters, timestamp)

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        return self._profiles.get(identity.user_id)
