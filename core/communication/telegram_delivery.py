# coding: utf-8
"""Отправка служебных сообщений через Bot API."""

from __future__ import annotations

from typing import Any

from ui.telegram_session import build_telegram_bot


async def send_telegram_text(
    config: dict[str, Any],
    *,
    chat_id: str | int,
    text: str,
) -> None:
    """Отправляет text в chat_id и закрывает session."""
    bot = build_telegram_bot(config)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    finally:
        await bot.session.close()
