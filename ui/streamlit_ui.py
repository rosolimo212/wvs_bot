# coding: utf-8
"""
Контракт виджетов Streamlit UI.

Используется в тестах: ключи виджетов и ожидаемые элементы по экранам.
"""

from __future__ import annotations

from core.models import Screen

START_WIDGET_KEYS = ("name_input", "btn_start")
MAIN_MENU_BUTTON_KEY_PREFIX = "btn_menu_"
MAIN_MENU_BUTTON_COUNT = 5

START_MESSAGE_NAMES = ("browser_name_label", "browser_btn_continue")
HEADER_MESSAGE_NAMES = ("browser_page_title", "browser_title")

SCREENS_WITH_DEDICATED_BRANCH = (
    Screen.START.value,
    Screen.MAIN_QUESTIONARY.value,
)

FORBIDDEN_STREAMLIT_PATTERNS = (
    "@st.cache_resource",
    "CookieManager",
    "extra_streamlit_components",
)

REQUIRED_COOKIE_READ = "st.context.cookies"
