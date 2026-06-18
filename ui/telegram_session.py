# coding: utf-8
"""
Создание Bot/session для aiogram с учётом config.yaml.

На многих VPS (в т.ч. в РФ) api.telegram.org недоступен или отвечает с таймаутом —
тогда нужен proxy_url в секции telegram.
"""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession


def build_telegram_bot(config: dict[str, Any]) -> Bot:
    """
    Собирает Bot с опциональным прокси и увеличенным таймаутом HTTP.

    :param config: результат load_app_config()
    """
    telegram_cfg = config["telegram"]
    token = telegram_cfg["token"]

    proxy_url = str(telegram_cfg.get("proxy_url") or "").strip() or None
    timeout_sec = float(telegram_cfg.get("request_timeout_sec", 60))

    # aiogram хранит timeout как число (секунды) и складывает с polling_timeout;
    # ClientTimeout здесь ломает start_polling.
    session = AiohttpSession(proxy=proxy_url, timeout=timeout_sec)
    return Bot(token=token, session=session)
