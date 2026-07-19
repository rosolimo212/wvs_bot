#!/usr/bin/env python3
# coding: utf-8
"""
Пересчёт country_rv / country_sv в country_data из gen_sample (единая методология).

Используйте после git pull, если gen_sample уже в БД, но индексы стран устарели:

  python3 scripts/recompute_reference_indices.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config
from core.reference_data import recompute_country_indices_from_gen_sample


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Пересчитать country_rv/country_sv в country_data из gen_sample"
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--schema", default=None)
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

    updated = recompute_country_indices_from_gen_sample(
        logging_config,
        reference_schema=reference_schema,
    )
    print(f"Обновлено строк country_data ({reference_schema}): {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
