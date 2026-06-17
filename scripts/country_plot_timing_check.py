#!/usr/bin/env python3
# coding: utf-8
"""Печать таймингов загрузки карты стран (для pre_commit_check)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.country_plot import format_country_plot_timings, measure_country_plot_pipeline

SAMPLE_COUNTRY_DATA = pd.DataFrame(
    [
        {"country_code": "RUS", "country_rv": 10.0, "country_sv": 12.0, "cluster": 1},
        {"country_code": "USA", "country_rv": 11.0, "country_sv": 13.0, "cluster": 2},
        {"country_code": "DEU", "country_rv": 9.5, "country_sv": 11.5, "cluster": 1},
        {"country_code": "JPN", "country_rv": 8.0, "country_sv": 14.0, "cluster": 3},
        {"country_code": "KOR", "country_rv": 7.5, "country_sv": 13.5, "cluster": 3},
    ]
)


def main() -> int:
    timings = measure_country_plot_pipeline(
        user_sv=12.0,
        user_rv=10.0,
        country_code="RUS",
        logging_config={"schema": "wvs"},
        country_df=SAMPLE_COUNTRY_DATA,
    )
    print(format_country_plot_timings(timings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
