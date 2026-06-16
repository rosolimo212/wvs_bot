#!/usr/bin/env python3
# coding: utf-8
"""Загрузка gen_sample.csv и country_data.csv в тестовую БД."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config
from core.reference_data import load_reference_data, reference_data_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Загрузить справочные CSV в postgres")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config.yaml",
        help="Путь к config.yaml",
    )
    parser.add_argument(
        "--gen-sample",
        type=Path,
        default=ROOT / "gen_sample.csv",
        help="Путь к gen_sample.csv",
    )
    parser.add_argument(
        "--country-data",
        type=Path,
        default=ROOT / "country_data.csv",
        help="Путь к country_data.csv",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Схема справочников (по умолчанию analytics.reference_schema или tl)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Только показать число строк в таблицах",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Не очищать таблицы перед загрузкой",
    )
    args = parser.parse_args()

    config = load_app_config(args.config)
    if not config.get("app", {}).get("logging_enabled"):
        print("В config.yaml нужно logging_enabled: true", file=sys.stderr)
        return 1

    logging_config = config["logging"]
    reference_schema = args.schema or config.get("analytics", {}).get("reference_schema", "tl")

    if args.status:
        status = reference_data_status(logging_config, reference_schema=reference_schema)
        for table, count in status.items():
            label = "нет таблицы" if count is None else str(count)
            print(f"{reference_schema}.{table}: {label}")
        return 0

    counts = load_reference_data(
        logging_config,
        reference_schema=reference_schema,
        gen_sample_path=args.gen_sample,
        country_data_path=args.country_data,
        truncate=not args.append,
    )
    print(
        f"Загружено в {reference_schema}: "
        f"gen_sample={counts['gen_sample']}, country_data={counts['country_data']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
