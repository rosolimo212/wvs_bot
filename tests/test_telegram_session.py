# coding: utf-8
"""Тесты сборки Telegram Bot session."""

from __future__ import annotations

from ui.telegram_session import build_telegram_bot


def test_build_telegram_bot_without_proxy() -> None:
    bot = build_telegram_bot(
        {
            "telegram": {
                "token": "123456:ABC",
                "proxy_url": "",
                "request_timeout_sec": 90,
            }
        }
    )
    assert bot.token == "123456:ABC"
