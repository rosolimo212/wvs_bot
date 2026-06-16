# coding: utf-8
"""Streamlit-клиент WVS."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.messages import button, message
from core.models import ACTION_NAME_ENTERED, Screen
from ui.base import build_app_service
from ui.helpers import (
    apply_response,
    build_payload,
    get_identity,
    init_user_identity,
)
from ui.streamlit_cookies import persist_external_id_cookie, resolve_external_user_id


def _init_session(service, state) -> None:
    """
    Первый прогон session_state.

    Экран после регистрации задаёт handle_start + postgres, не cookie.
    """
    if state.get("initialized"):
        return
    state["initialized"] = True

    identity = init_user_identity(service, state, "streamlit")
    response = service.handle_start(identity, "streamlit")

    reg_name = None
    reg_date = None
    profile = service.logger.get_user_profile(identity)
    if profile:
        name = str(profile.get("user_name") or "").strip()
        if name:
            reg_name = name
            reg = profile.get("registration_date")
            if isinstance(reg, datetime):
                reg_date = reg.isoformat()
            elif reg is not None:
                reg_date = str(reg)

    apply_response(state, response, user_name=reg_name, registration_date=reg_date)


def _registered_payload(state) -> dict[str, Any]:
    return build_payload(
        user_name=getattr(state, "user_name", None),
        registration_date=getattr(state, "registration_date", None),
    )


def _handle_user_input(service, state, text: str) -> None:
    identity = get_identity(state)
    screen = getattr(state, "screen", Screen.START.value)

    if screen == Screen.START.value:
        response = service.handle_action(
            identity,
            "streamlit",
            ACTION_NAME_ENTERED,
            build_payload(text=text),
        )
        user_name = None
        reg_date = None
        if response.screen == Screen.MAIN_MENU:
            user_name = text.strip()
            reg_date = datetime.now().isoformat()
        apply_response(
            state,
            response,
            user_name=user_name,
            registration_date=reg_date,
        )
        return

    response = service.handle_action(
        identity,
        "streamlit",
        "raw",
        {
            **_registered_payload(state),
            **build_payload(text=text, screen=screen),
        },
    )
    apply_response(state, response)


def run_streamlit(config: dict[str, Any]) -> None:
    import streamlit as st

    st.set_page_config(
        page_title=message("browser_page_title", "streamlit"),
        page_icon="🌍",
    )

    service = build_app_service(config)
    state = st.session_state

    resolve_external_user_id(state, st.context.cookies)

    if not state.get("initialized"):
        _init_session(service, state)

    st.title(message("browser_title", "streamlit"))
    st.caption(
        f"user_id: {state.user_id[:12]}… | "
        f"internal: {state.internal_user_id} | "
        f"external: {state.external_user_id[:8]}… | "
        f"экран: {state.screen}"
    )
    st.markdown(state.get("last_text", ""))

    screen = state.get("screen", Screen.START.value)

    if screen == Screen.START.value:
        name = st.text_input(message("browser_name_label", "streamlit"), key="name_input")
        if st.button(message("browser_btn_continue", "streamlit"), key="btn_start"):
            _handle_user_input(service, state, name)
            st.rerun()

    else:
        buttons = state.get("buttons", [])
        for idx, label in enumerate(buttons):
            if st.button(label, key=f"btn_menu_{idx}"):
                _handle_user_input(service, state, label)
                st.rerun()

    if state.get("external_user_id"):
        persist_external_id_cookie(str(state["external_user_id"]))


if __name__ == "__main__":
    from core.config import load_app_config

    run_streamlit(load_app_config(ROOT / "config.yaml"))
