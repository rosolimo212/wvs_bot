#!/usr/bin/env python3
# coding: utf-8
"""
Импорт legacy-данных Telegram-бота из CSV в prod-таблицы wvs.

Пример:
  python3 scripts/import_legacy_bot.py --dry-run
  python3 scripts/import_legacy_bot.py --prod
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config
from core.migration.legacy_import import import_legacy_bot

LEGACY_DIR = ROOT / "scripts" / "migrate_legacy"


def _resolve_logging_config(config_path: Path, target: str) -> dict[str, Any]:
    if target == "logging":
        return load_app_config(config_path)["logging"]
    with config_path.open("r", encoding="utf-8") as handle:
        full = yaml.full_load(handle)
    section = full.get(target)
    if not isinstance(section, dict):
        raise ValueError(f"Секция {target!r} не найдена в {config_path}")
    for key in ("host", "port", "database", "user", "password", "schema"):
        if key not in section:
            raise ValueError(f"В секции {target!r} обязателен ключ {key!r}")
    return section


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Импорт legacy CSV (Telegram ID) в wvs.users / user_answers / user_reviews / events"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--users",
        type=Path,
        default=LEGACY_DIR / "users.csv",
        help="CSV с пользователями (external_user_id, user_name, registration_time)",
    )
    parser.add_argument(
        "--main-answers",
        type=Path,
        default=LEGACY_DIR / "user_answers.csv",
        help="CSV с ответами основной анкеты",
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=LEGACY_DIR / "user_reviews.csv",
        help="CSV с ответами доп. анкеты",
    )
    parser.add_argument(
        "--events",
        type=Path,
        default=LEGACY_DIR / "events.csv",
        help="CSV с событиями",
    )
    parser.add_argument(
        "--target",
        choices=("logging", "wvs_dev", "wvs_prod"),
        default="logging",
        help="Секция БД в config.yaml (logging=localhost, wvs_prod=prod VM)",
    )
    parser.add_argument(
        "--prod",
        action="store_const",
        const="wvs_prod",
        dest="target",
        help="Краткая форма --target wvs_prod",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только подсчёт строк без записи в БД",
    )
    args = parser.parse_args()

    paths = (args.users, args.main_answers, args.reviews, args.events)
    for path in paths:
        if path and not path.is_file():
            print(f"Файл не найден: {path}", file=sys.stderr)
            return 1

    logging_config = _resolve_logging_config(args.config, args.target)
    stats = import_legacy_bot(
        logging_config,
        users_csv=args.users if args.users else None,
        main_answers_csv=args.main_answers,
        reviews_csv=args.reviews,
        events_csv=args.events,
        dry_run=args.dry_run,
    )

    mode = "DRY-RUN" if args.dry_run else "IMPORT"
    print(f"[{mode}] target={args.target} host={logging_config['host']}")
    print(f"[{mode}] users created={stats.users_created} skipped={stats.users_skipped}")
    print(f"[{mode}] main_answers={stats.main_answers} reviews={stats.reviews}")
    print(
        f"[{mode}] events imported={stats.events_imported} skipped={stats.events_skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
