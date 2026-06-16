# coding: utf-8
"""
Точка входа приложения.

Цель:
    Прочитать config.yaml, выбрать интерфейс и запустить нужный клиент.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config


def main() -> None:
    config = load_app_config("config.yaml")
    interface = config["app"]["interface"]

    if interface == "streamlit":
        from ui.streamlit_app import run_streamlit

        run_streamlit(config)
    elif interface == "telegram":
        from ui.telegram_bot import run_telegram

        asyncio.run(run_telegram(config))
    elif interface == "console":
        from ui.console_app import run_console

        run_console(config)
    else:
        raise ValueError(
            f"Неизвестный интерфейс: {interface!r}. "
            "Ожидается streamlit, telegram или console."
        )


if __name__ == "__main__":
    main()
