#!/usr/bin/env python3
# coding: utf-8
"""Ручная отправка исходящей коммуникации (сегмент + template)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Отправить communication-шаблон сегменту пользователей Telegram",
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--template",
        required=True,
        help="template_id из data/communication_messages.json",
    )
    parser.add_argument(
        "--segment",
        required=True,
        choices=("test", "all_users", "primary_complete", "both_complete"),
        help="Сегмент получателей",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать план без отправки и без записи в communications",
    )
    parser.add_argument(
        "--pause-sec",
        type=float,
        default=2.0,
        help="Пауза между сообщениями внутри прогона (сек)",
    )
    parser.add_argument(
        "--messages",
        type=Path,
        default=None,
        help="Путь к communication_messages.json (по умолчанию data/...)",
    )
    args = parser.parse_args()

    from core.communication.campaigns import format_run_summary, run_communication
    from core.config import load_app_config

    config = load_app_config(args.config)
    result = asyncio.run(
        run_communication(
            config,
            template_id=args.template,
            segment=args.segment,
            dry_run=args.dry_run,
            messages_path=args.messages,
            pause_sec=args.pause_sec,
        )
    )
    print(format_run_summary(result))
    if args.dry_run:
        print("\n[dry-run] ничего не отправлено", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
