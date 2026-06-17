#!/usr/bin/env python3
# coding: utf-8
"""Проверка доступа к Telegram Bot API с этой машины (перед запуском бота)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def _check(config_path: Path) -> int:
    import aiohttp
    from core.config import load_app_config
    from ui.telegram_session import build_telegram_bot

    config = load_app_config(config_path)
    telegram_cfg = config["telegram"]
    proxy = str(telegram_cfg.get("proxy_url") or "").strip() or None
    timeout = int(telegram_cfg.get("request_timeout_sec", 60))

    print("1) Прямой HTTPS к api.telegram.org ...")
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as session:
            async with session.get("https://api.telegram.org") as response:
                print(f"   OK: HTTP {response.status}")
    except Exception as exc:
        print(f"   FAIL: {exc}")
        print("   Скорее всего нужен proxy_url в config.yaml → telegram")

    print("2) getMe через aiogram (с proxy/timeout из config) ...")
    bot = build_telegram_bot(config)
    try:
        me = await bot.get_me()
        print(f"   OK: @{me.username} (id={me.id})")
        return 0
    except Exception as exc:
        print(f"   FAIL: {exc}")
        return 1
    finally:
        await bot.session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка Telegram API")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    args = parser.parse_args()

    import asyncio

    return asyncio.run(_check(args.config))


if __name__ == "__main__":
    raise SystemExit(main())
