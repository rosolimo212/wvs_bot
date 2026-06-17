# coding: utf-8
"""Общие фикстуры pytest."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config) -> None:
    # matplotlib тянет устаревший API pyparsing — не наш код.
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pyparsing.warnings.PyparsingDeprecationWarning:matplotlib",
    )
