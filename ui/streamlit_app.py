# coding: utf-8
"""Streamlit-клиент WVS."""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.messages import back_to_learn_more_button, back_to_menu_button, button, message
from core.country_profiles import format_country_profile
from core.error_reporting import analytics_feature_label, describe_exception
from core.learn_more import match_learn_more_question
from core.models import (
    ACTION_BACK_TO_MENU,
    ACTION_LEARN_MORE_ITEM,
    ACTION_MAIN_ANSWER,
    ACTION_MAIN_RETURN_LATER,
    ACTION_NAME_ENTERED,
    ACTION_SECONDARY_ANSWER,
    ACTION_SECONDARY_RETURN_LATER,
    Screen,
)
from ui.base import build_app_service
from ui.helpers import (
    apply_response,
    build_payload,
    get_identity,
    init_user_identity,
    with_screen_context,
)
from ui.streamlit_cookies import persist_external_id_cookie, resolve_external_user_id

FAVICON_PATH = ROOT / "hqdefault.jpg"


def _page_icon() -> str:
    """Фавикон: hqdefault.jpg в корне проекта или emoji по умолчанию."""
    return str(FAVICON_PATH) if FAVICON_PATH.is_file() else "🌍"


def _streamlit_buttons_nav_first(buttons: list[str], channel: str = "streamlit") -> list[str]:
    """Навигационные кнопки — первыми, слева."""
    back_lm = back_to_learn_more_button(channel)
    back = back_to_menu_button(channel)
    ordered: list[str] = []
    if back_lm in buttons:
        ordered.append(back_lm)
    if back in buttons:
        ordered.append(back)
    ordered.extend(label for label in buttons if label not in (back_lm, back))
    return ordered


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
        with_screen_context(
            state,
            {
                **_registered_payload(state),
                **build_payload(text=text, screen=screen),
            },
        ),
    )
    apply_response(state, response)


def _render_questionnaire_screen(
    service,
    state,
    identity,
    *,
    screen: str,
    answer_action: str,
    return_action: str,
    key_prefix: str,
    on_answer,
) -> None:
    import streamlit as st

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
            key=f"{key_prefix}_text_{qv_number}",
            placeholder="Введите ответ...",
            label_visibility="collapsed",
        )
        if choice_buttons:
            selected = st.radio(
                "Или выберите вариант",
                choice_buttons,
                key=f"{key_prefix}_q_{qv_number}",
                label_visibility="collapsed",
            )
        else:
            selected = ""
    else:
        selected = st.radio(
            "Выберите ответ",
            choice_buttons,
            key=f"{key_prefix}_q_{qv_number}",
            label_visibility="collapsed",
        )

    col1, col2 = st.columns([1, 4])
    submit_label = message("browser_btn_submit", "streamlit")
    with col1:
        if st.button(return_later_label, key=f"{key_prefix}_return_{qv_number}"):
            response = service.handle_action(
                identity,
                "streamlit",
                return_action,
                _registered_payload(state),
            )
            apply_response(state, response)
            st.rerun()
    with col2:
        if st.button(submit_label, key=f"{key_prefix}_submit_{qv_number}"):
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
                answer_action,
                {
                    **_registered_payload(state),
                    **build_payload(screen=screen),
                    "answer": answer,
                    "selected": selected_value,
                },
            )
            apply_response(state, response)
            on_answer(identity)
            st.rerun()


def run_streamlit(config: dict[str, Any]) -> None:
    import streamlit as st

    st.set_page_config(
        page_title=message("browser_page_title", "streamlit"),
        page_icon=_page_icon(),
    )

    service = build_app_service(config)
    state = st.session_state

    resolve_external_user_id(state, st.context.cookies)

    if not state.get("initialized"):
        _init_session(service, state)

    identity = get_identity(state)

    st.title(message("browser_title", "streamlit"))
    if config.get("app", {}).get("debug_ui", False):
        st.caption(
            f"user_id: {state.user_id[:12]}… | "
            f"internal: {state.internal_user_id} | "
            f"external: {state.external_user_id[:8]}… | "
            f"экран: {state.screen}"
        )
    st.markdown(state.get("last_text", ""))

    screen = state.get("screen", Screen.START.value)
    if screen != Screen.FIND_COUNTRY.value:
        state.pop("country_plot_logged", None)

    meta = state.get("meta", {})
    if (
        screen == Screen.FIND_COUNTRY.value
        and meta.get("show_country_plot")
        and meta.get("user_rv") is not None
        and not state.get("country_plot_logged")
    ):
        logging_config = config.get("logging") if config.get("app", {}).get("logging_enabled") else None
        if logging_config:
            from ui.country_plot import build_country_plot_plotly

            reference_schema = str(
                config.get("analytics", {}).get("reference_schema")
                or config.get("logging", {}).get("schema", "wvs")
            )
            total_started = time.perf_counter()
            try:
                fig, build_timings = build_country_plot_plotly(
                    float(meta["user_sv"]),
                    float(meta["user_rv"]),
                    logging_config,
                    reference_schema=reference_schema,
                )
            except Exception as exc:
                service.log_analytics_error(
                    identity,
                    "streamlit",
                    feature="country_plot",
                    exc=exc,
                )
                details = describe_exception(exc)
                st.error(
                    message(
                        "analytics_error",
                        "streamlit",
                        feature=analytics_feature_label("country_plot"),
                        module=details["module"],
                        error_name=details["error_name"],
                        error_message=details["error_message"],
                    )
                )
                state["country_plot_logged"] = True
            else:
                if fig is not None:
                    render_started = time.perf_counter()
                    st.plotly_chart(fig, use_container_width=True)
                    render_ms = int((time.perf_counter() - render_started) * 1000)

                    profile_started = time.perf_counter()
                    country_code = str(meta.get("country_code", ""))
                    profile_text = format_country_profile(country_code, "streamlit")
                    if profile_text.strip():
                        st.markdown(profile_text)
                    country_plot_loaded_ms = int((time.perf_counter() - profile_started) * 1000)

                    total_ms = int((time.perf_counter() - total_started) * 1000)
                    service.log_country_plot_loaded(
                        identity,
                        "streamlit",
                        sql_ms=build_timings.sql_ms,
                        processing_ms=build_timings.processing_ms,
                        render_ms=render_ms,
                        country_plot_loaded_ms=country_plot_loaded_ms,
                        total_ms=total_ms,
                    )
                    state["country_plot_logged"] = True

    if screen != Screen.FIND_OWN_PLACE.value:
        state.pop("own_place_charts_logged", None)

    own_place_meta = state.get("meta", {})
    if (
        screen == Screen.FIND_OWN_PLACE.value
        and own_place_meta.get("show_own_place_charts")
        and not state.get("own_place_charts_logged")
    ):
        from ui.own_place_plot import build_index_histogram_plotly

        for chart in own_place_meta.get("own_place_charts", []):
            fig = build_index_histogram_plotly(
                list(chart["peer_values"]),
                float(chart["user_value"]),
                title=str(chart["title"]),
                x_label=str(chart["x_label"]),
            )
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
        state["own_place_charts_logged"] = True

    if screen == Screen.START.value:
        name = st.text_input(message("browser_name_label", "streamlit"), key="name_input")
        if st.button(message("browser_btn_continue", "streamlit"), key="btn_start"):
            _handle_user_input(service, state, name)
            st.rerun()

    elif screen == Screen.MAIN_QUESTIONARY.value:
        _render_questionnaire_screen(
            service,
            state,
            identity,
            screen=screen,
            answer_action=ACTION_MAIN_ANSWER,
            return_action=ACTION_MAIN_RETURN_LATER,
            key_prefix="main",
            on_answer=lambda ident: state.update(
                {"main_questionary_complete": service.is_main_questionary_complete(ident)}
            ),
        )

    elif screen == Screen.SECONDARY_QUESTIONARY.value:
        _render_questionnaire_screen(
            service,
            state,
            identity,
            screen=screen,
            answer_action=ACTION_SECONDARY_ANSWER,
            return_action=ACTION_SECONDARY_RETURN_LATER,
            key_prefix="secondary",
            on_answer=lambda _ident: None,
        )

    else:
        buttons = _streamlit_buttons_nav_first(state.get("buttons", []), "streamlit")
        for idx, label in enumerate(buttons):
            if st.button(label, key=f"btn_menu_{idx}"):
                if label == back_to_menu_button("streamlit"):
                    response = service.handle_action(
                        identity,
                        "streamlit",
                        ACTION_BACK_TO_MENU,
                        {
                            **_registered_payload(state),
                            **build_payload(screen=screen),
                        },
                    )
                    apply_response(state, response)
                elif screen in (Screen.LEARN_MORE.value, Screen.LEARN_MORE_ANSWER.value):
                    faq_item = match_learn_more_question(label, "streamlit")
                    if faq_item is not None:
                        response = service.handle_action(
                            identity,
                            "streamlit",
                            ACTION_LEARN_MORE_ITEM,
                            {
                                **_registered_payload(state),
                                **build_payload(screen=screen),
                                "learn_more_item": faq_item,
                            },
                        )
                        apply_response(state, response)
                    else:
                        _handle_user_input(service, state, label)
                else:
                    _handle_user_input(service, state, label)
                state["main_questionary_complete"] = service.is_main_questionary_complete(identity)
                st.rerun()

    if state.get("external_user_id"):
        persist_external_id_cookie(str(state["external_user_id"]))


if __name__ == "__main__":
    from core.config import load_app_config

    run_streamlit(load_app_config(ROOT / "config.yaml"))
