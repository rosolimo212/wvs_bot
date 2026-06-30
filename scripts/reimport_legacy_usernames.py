#!/usr/bin/env python3
# coding: utf-8
"""
Импорт отдельных legacy-пользователей из схемы tl по user_name.

Пример:
  python3 scripts/reimport_legacy_usernames.py --prod Rkhbvs kirsl
  python3 scripts/reimport_legacy_usernames.py --dry-run --prod Rkhbvs
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

from core.migration.legacy_import import import_legacy_from_tl_by_usernames


def _resolve_logging_config(config_path: Path, target: str) -> dict[str, Any]:
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
        description="Импорт legacy-пользователей из tl.* по user_name"
    )
    parser.add_argument("usernames", nargs="+", help="user_name в legacy (например Rkhbvs kirsl)")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--target",
        choices=("logging", "wvs_dev", "wvs_prod"),
        default="logging",
    )
    parser.add_argument("--prod", action="store_const", const="wvs_prod", dest="target")
    parser.add_argument("--legacy-schema", default="tl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging_config = _resolve_logging_config(args.config, args.target)
    stats = import_legacy_from_tl_by_usernames(
        logging_config,
        args.usernames,
        legacy_schema=args.legacy_schema,
        dry_run=args.dry_run,
    )

    mode = "DRY-RUN" if args.dry_run else "IMPORT"
    print(f"[{mode}] target={args.target} host={logging_config['host']}")
    print(f"[{mode}] usernames={args.usernames}")
    print(f"[{mode}] users created={stats.users_created} skipped={stats.users_skipped}")
    print(f"[{mode}] main_answers={stats.main_answers} reviews={stats.reviews}")
    print(
        f"[{mode}] events imported={stats.events_imported} "
        f"skipped={stats.events_skipped}"
    )
    if stats.users_created == 0 and stats.main_answers == 0:
        print("Ничего не найдено в legacy-схеме — проверьте user_name и схему tl.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
