#!/usr/bin/env python3
# coding: utf-8
"""
Импорт legacy-данных Telegram-бота из трёх CSV в prod-таблицы wvs.

Пример:
  python3 scripts/import_legacy_bot.py \\
    --main-answers scripts/migrate_legacy/main_answers.csv \\
    --reviews scripts/migrate_legacy/reviews.csv \\
    --events scripts/migrate_legacy/events.csv

  python3 scripts/import_legacy_bot.py --dry-run ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config
from core.migration.legacy_import import import_legacy_bot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Импорт legacy CSV (Telegram ID) в wvs.users / user_answers / user_reviews / events"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--main-answers",
        type=Path,
        required=True,
        help="CSV с ответами основной анкеты (tl.user_answers)",
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        required=True,
        help="CSV с ответами доп. анкеты (tl.user_reviews)",
    )
    parser.add_argument(
        "--events",
        type=Path,
        required=True,
        help="CSV с событиями (tl.wvs_events)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только подсчёт строк без записи в БД",
    )
    args = parser.parse_args()

    for path in (args.main_answers, args.reviews, args.events):
        if not path.is_file():
            print(f"Файл не найден: {path}", file=sys.stderr)
            return 1

    config = load_app_config(args.config)
    logging_config = config["logging"]
    stats = import_legacy_bot(
        logging_config,
        main_answers_csv=args.main_answers,
        reviews_csv=args.reviews,
        events_csv=args.events,
        dry_run=args.dry_run,
    )

    mode = "DRY-RUN" if args.dry_run else "IMPORT"
    print(f"[{mode}] users created={stats.users_created} skipped={stats.users_skipped}")
    print(f"[{mode}] main_answers={stats.main_answers} reviews={stats.reviews}")
    print(
        f"[{mode}] events imported={stats.events_imported} skipped={stats.events_skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
