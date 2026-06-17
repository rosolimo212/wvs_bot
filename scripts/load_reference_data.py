#!/usr/bin/env python3
# coding: utf-8
"""Загрузка gen_sample.csv и country_data.csv в postgres (обёртка над setup_reference_tables)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "setup_reference_tables.py"
    sys.argv[0] = str(script)
    runpy.run_path(str(script), run_name="__main__")
