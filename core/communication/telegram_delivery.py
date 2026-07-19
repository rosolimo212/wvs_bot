# coding: utf-8
"""Отправка служебных сообщений через Bot API."""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode

from ui.telegram_session import build_telegram_bot


async def send_telegram_text(
    config: dict[str, Any],
    *,
    chat_id: str | int,
    text: str,
    parse_mode: ParseMode | str | None = None,
    bot: Bot | None = None,
) -> None:
    """Отправляет text в chat_id. Если bot не передан — создаёт и закрывает session."""
    owns_bot = bot is None
    active = bot or build_telegram_bot(config)
    try:
        await active.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    finally:
        if owns_bot:
            await active.session.close()
