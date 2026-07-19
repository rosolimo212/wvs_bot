#!/usr/bin/env python3
# coding: utf-8
"""Ежедневный отчёт активности аудитории в служебный Telegram-чат."""

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
        description="Собрать метрики аудитории и отправить в Telegram-чат",
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только напечатать отчёт, не отправлять и не учитывать send_at",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Отправить сейчас, игнорируя send_at и маркер «уже отправлено сегодня»",
    )
    parser.add_argument(
        "--chat-id",
        default=None,
        help="Переопределить communication.daily_audience_report.chat_id",
    )
    args = parser.parse_args()

    from core.communication.daily_audience import run_daily_audience_report
    from core.config import load_app_config

    config = load_app_config(args.config)
    result = asyncio.run(
        run_daily_audience_report(
            config,
            dry_run=args.dry_run,
            force=args.force,
            chat_id=args.chat_id,
        )
    )
    if result.skipped_reason and result.skipped_reason not in {"dry_run"}:
        print(f"skip: {result.skipped_reason}", file=sys.stderr)
        return 0
    if result.text:
        print(result.text)
    if args.dry_run:
        print("\n[dry-run] сообщение не отправлено", file=sys.stderr)
    elif result.sent:
        print("\n[ok] отправлено", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
