#!/usr/bin/env python3
# coding: utf-8
"""
Создание и наполнение справочных таблиц gen_sample и country_data.

Шаги:
  1. CREATE SCHEMA + таблицы (sql/005_reference_schema.sql)
  2. COPY из gen_sample.csv и country_data.csv
  3. UPDATE country_data полями из data/country_profiles.json

Примеры:
  python3 scripts/setup_reference_tables.py
  python3 scripts/setup_reference_tables.py --create-only
  python3 scripts/setup_reference_tables.py --status
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config
from core.reference_data import reference_data_status, setup_reference_tables


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Создать gen_sample и country_data, загрузить CSV, обогатить профилями"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--gen-sample", type=Path, default=ROOT / "gen_sample.csv")
    parser.add_argument("--country-data", type=Path, default=ROOT / "country_data.csv")
    parser.add_argument(
        "--profiles",
        type=Path,
        default=ROOT / "data" / "country_profiles.json",
        help="JSON с полями full_name, government_type и др.",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Схема справочников (по умолчанию logging.schema или wvs)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Только показать число строк в таблицах",
    )
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Только создать таблицы, без CSV и без обогащения",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Не обновлять country_data из country_profiles.json",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Не очищать таблицы перед загрузкой CSV",
    )
    args = parser.parse_args()

    config = load_app_config(args.config)
    if not config.get("app", {}).get("logging_enabled"):
        print("В config.yaml нужно logging_enabled: true", file=sys.stderr)
        return 1

    logging_config = config["logging"]
    reference_schema = (
        args.schema
        or config.get("analytics", {}).get("reference_schema")
        or logging_config.get("schema", "wvs")
    )

    if args.status:
        status = reference_data_status(logging_config, reference_schema=reference_schema)
        for table, count in status.items():
            label = "нет таблицы" if count is None else str(count)
            print(f"{reference_schema}.{table}: {label}")
        return 0

    counts = setup_reference_tables(
        logging_config,
        reference_schema=reference_schema,
        gen_sample_path=args.gen_sample,
        country_data_path=args.country_data,
        profiles_path=args.profiles,
        truncate=not args.append,
        load_csv=not args.create_only,
        enrich_profiles=not args.create_only and not args.no_enrich,
    )

    if args.create_only:
        print(f"Созданы таблицы в схеме {reference_schema}: gen_sample, country_data")
        return 0

    print(
        f"Готово ({reference_schema}): "
        f"gen_sample={counts.get('gen_sample')}, "
        f"country_data={counts.get('country_data')}, "
        f"country_index_updates={counts.get('country_index_updates')}, "
        f"profile_updates={counts.get('profile_updates')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
