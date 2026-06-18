# coding: utf-8
"""
Общие функции для UI-клиентов (streamlit, telegram, console).

Цель:
    Связать session state интерфейса с AppService: identity, payload, AppResponse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.identity import new_external_user_id
from core.models import AppResponse, Screen, UserIdentity


def build_payload(
    user_name: str | None = None,
    registration_date: str | datetime | None = None,
    text: str | None = None,
    screen: Screen | str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    if user_name:
        payload["user_name"] = user_name

    if registration_date is not None:
        if isinstance(registration_date, datetime):
            payload["registration_date"] = registration_date.isoformat()
        else:
            payload["registration_date"] = registration_date

    if text is not None:
        payload["text"] = text

    if screen is not None:
        if isinstance(screen, Screen):
            payload["screen"] = screen.value
        else:
            payload["screen"] = screen

    return payload


def with_screen_context(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Добавить в payload контекст текущего экрана из session state."""
    merged = dict(payload)
    learn_more_item = (state.get("meta") or {}).get("learn_more_item")
    if learn_more_item is not None:
        merged["learn_more_item"] = learn_more_item
    return merged


def apply_response(
    state: dict[str, Any],
    response: AppResponse,
    *,
    user_name: str | None = None,
    registration_date: str | None = None,
) -> None:
    state["last_text"] = response.text
    state["screen"] = response.screen.value
    state["buttons"] = list(response.buttons)
    state["meta"] = dict(response.meta)

    if "main_questionary_complete" in response.meta:
        state["main_questionary_complete"] = bool(response.meta["main_questionary_complete"])

    if user_name is not None:
        state["user_name"] = user_name

    if registration_date is not None:
        state["registration_date"] = registration_date


def store_identity(state: dict[str, Any], identity: UserIdentity) -> None:
    state["user_id"] = identity.user_id
    state["internal_user_id"] = identity.internal_user_id
    state["external_user_id"] = identity.external_user_id


def get_identity(state: dict[str, Any]) -> UserIdentity:
    return UserIdentity(
        user_id=str(state["user_id"]),
        internal_user_id=int(state["internal_user_id"]),
        external_user_id=str(state["external_user_id"]),
    )


def init_user_identity(service, state: dict[str, Any], channel: str) -> UserIdentity:
    if (
        state.get("user_id")
        and state.get("internal_user_id") is not None
        and state.get("external_user_id")
    ):
        return get_identity(state)

    if not state.get("external_user_id"):
        state["external_user_id"] = new_external_user_id(channel)

    identity = service.logger.ensure_user(channel, str(state["external_user_id"]))
    store_identity(state, identity)
    return identity
