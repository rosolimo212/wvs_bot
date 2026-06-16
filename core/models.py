# coding: utf-8
"""
Общие структуры данных ядра.

Цель:
    Единые типы для users, events и ответов UI без привязки к конкретному клиенту.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class UserIdentity:
    """
    Тройка идентификаторов пользователя.

    user_id — sha256(channel:external_user_id), PK в postgres.
    internal_user_id — BIGSERIAL для аналитики и FK.
    external_user_id — uuid (streamlit/console) или telegram id.
    """

    user_id: str
    internal_user_id: int
    external_user_id: str


class Screen(str, Enum):
    """Экраны пользовательского сценария WVS."""

    START = "start"
    NAME_CONFIRM = "name_confirm"
    MAIN_MENU = "main_menu"
    MAIN_QUESTIONARY = "main_questionary"
    SECONDARY_QUESTIONARY = "secondary_questionary"
    FIND_COUNTRY = "find_country"
    FIND_OWN_PLACE = "find_own_place"


ACTION_NAME_ENTERED = "name_entered"
ACTION_NAME_CONFIRMED = "name_confirmed"
ACTION_NAME_CHANGE = "name_change"
ACTION_OPTION_1 = "option_1"
ACTION_OPTION_2 = "option_2"
ACTION_OPTION_3 = "option_3"
ACTION_OPTION_4 = "option_4"
ACTION_BACK_TO_MENU = "back_to_menu"
ACTION_MAIN_ANSWER = "main_answer"
ACTION_MAIN_RETURN_LATER = "main_return_later"


@dataclass
class UserRecord:
    """Запись пользователя для таблицы wvs.users."""

    user_id: str
    internal_user_id: int
    external_user_id: str
    user_name: str
    registration_date: datetime
    registration_channel: str
    last_active_at: datetime
    is_paid: bool = False
    is_trial: bool = False
    is_active: bool = True


@dataclass
class EventRecord:
    """Запись события для таблицы wvs.events."""

    timestamp: datetime
    user_id: str
    internal_user_id: int
    external_user_id: str
    event_name: str
    channel: str
    event_parameters: dict[str, Any] | None = None


@dataclass
class AppResponse:
    """
    Ответ ядра клиенту после обработки шага сценария.

    UI не решает бизнес-логику — только показывает text/buttons и переходит на screen.
  """

    text: str
    buttons: list[str] = field(default_factory=list)
    screen: Screen = Screen.START
    finished: bool = False
    meta: dict[str, Any] = field(default_factory=dict)
