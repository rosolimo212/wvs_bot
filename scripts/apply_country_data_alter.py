#!/usr/bin/env python3
# coding: utf-8
"""Применяет ALTER TABLE для country_data (доп. поля профиля страны)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config
from core.db import postgres_connection


def main() -> int:
    parser = argparse.ArgumentParser(description="ALTER TABLE country_data")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument(
        "--schema",
        default=None,
        help="Схема country_data (по умолчанию analytics.reference_schema или tl)",
    )
    args = parser.parse_args()

    config = load_app_config(args.config)
    if not config.get("app", {}).get("logging_enabled"):
        print("Нужен logging_enabled: true в config.yaml", file=sys.stderr)
        return 1

    schema = (
        args.schema
        or config.get("analytics", {}).get("reference_schema")
        or config["logging"].get("schema", "wvs")
    )
    statements = [
        f"ALTER TABLE {schema}.country_data ADD COLUMN IF NOT EXISTS full_name TEXT",
        f"ALTER TABLE {schema}.country_data ADD COLUMN IF NOT EXISTS government_type TEXT",
        f"ALTER TABLE {schema}.country_data ADD COLUMN IF NOT EXISTS gdp_per_capita_usd BIGINT",
        f"ALTER TABLE {schema}.country_data ADD COLUMN IF NOT EXISTS population BIGINT",
        f"ALTER TABLE {schema}.country_data ADD COLUMN IF NOT EXISTS flight_hours_from_london NUMERIC(5, 1)",
    ]

    with postgres_connection(config["logging"]) as conn:
        with conn.cursor() as cur:
            for sql in statements:
                cur.execute(sql)

    print(f"Готово: {schema}.country_data дополнена полями профиля")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
