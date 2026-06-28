# coding: utf-8
"""
Форматирование текста для Telegram (HTML parse_mode).

Цель:
    Streamlit понимает **bold**; Telegram legacy Markdown — нет. Конвертируем в <b>.

Вход:
    Текст с **фрагментами**.

Выход:
    HTML-строка с экранированием &, <, >.
"""

from __future__ import annotations

import html
import re

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def markdown_bold_to_telegram_html(text: str) -> str:
    """Преобразует **жирный** markdown в Telegram HTML."""
    parts = _BOLD_PATTERN.split(text)
    chunks: list[str] = []
    for index, part in enumerate(parts):
        escaped = html.escape(part)
        if index % 2 == 1:
            chunks.append(f"<b>{escaped}</b>")
        else:
            chunks.append(escaped)
    return "".join(chunks)
