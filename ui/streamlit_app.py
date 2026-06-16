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
from core.models import ACTION_MAIN_ANSWER, ACTION_MAIN_RETURN_LATER, ACTION_NAME_ENTERED, Screen
from ui.base import build_app_service
from ui.helpers import (
    apply_response,
    build_payload,
    get_identity,
    init_user_identity,
)
from ui.streamlit_cookies import persist_external_id_cookie, resolve_external_user_id


def _init_session(service, state) -> None:
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
    state["main_questionary_complete"] = service.is_main_questionary_complete(identity)


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
        apply_response(state, response, user_name=user_name, registration_date=reg_date)
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

    identity = get_identity(state)

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

    elif screen == Screen.MAIN_QUESTIONARY.value:
        meta = state.get("meta", {})
        buttons = state.get("buttons", [])
        return_later_label = meta.get("return_later_label", button("return_later", "streamlit"))
        qv_number = meta.get("qv_number", 0)
        input_mode = meta.get("input_mode", "choice")
        choice_buttons = [b for b in buttons if b != return_later_label]

        custom_text = ""
        if input_mode == "text":
            custom_text = st.text_input(
                "Введите ответ",
                key=f"main_text_{qv_number}",
                placeholder="Введите ответ...",
                label_visibility="collapsed",
            )
            if choice_buttons:
                selected = st.radio(
                    "Или выберите вариант",
                    choice_buttons,
                    key=f"main_q_{qv_number}",
                    label_visibility="collapsed",
                )
            else:
                selected = ""
        else:
            selected = st.radio(
                "Выберите ответ",
                choice_buttons,
                key=f"main_q_{qv_number}",
                label_visibility="collapsed",
            )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button(message("browser_btn_submit", "streamlit"), key=f"main_submit_{qv_number}"):
                if input_mode == "text":
                    if custom_text.strip():
                        answer = custom_text.strip()
                        selected_value = ""
                    else:
                        answer = selected
                        selected_value = selected
                else:
                    answer = selected
                    selected_value = selected
                response = service.handle_action(
                    identity,
                    "streamlit",
                    ACTION_MAIN_ANSWER,
                    {
                        **_registered_payload(state),
                        **build_payload(screen=screen),
                        "answer": answer,
                        "selected": selected_value,
                    },
                )
                apply_response(state, response)
                state["main_questionary_complete"] = service.is_main_questionary_complete(identity)
                st.rerun()
        with col2:
            if st.button(return_later_label, key=f"main_return_{qv_number}"):
                response = service.handle_action(
                    identity,
                    "streamlit",
                    ACTION_MAIN_RETURN_LATER,
                    _registered_payload(state),
                )
                apply_response(state, response)
                st.rerun()

    else:
        buttons = state.get("buttons", [])
        for idx, label in enumerate(buttons):
            if st.button(label, key=f"btn_menu_{idx}"):
                _handle_user_input(service, state, label)
                state["main_questionary_complete"] = service.is_main_questionary_complete(identity)
                st.rerun()

    if state.get("external_user_id"):
        persist_external_id_cookie(str(state["external_user_id"]))


if __name__ == "__main__":
    from core.config import load_app_config

    run_streamlit(load_app_config(ROOT / "config.yaml"))
