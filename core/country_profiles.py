# coding: utf-8
"""Профили стран для экрана «Найти страну»."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.messages import message

PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "country_profiles.json"


@lru_cache(maxsize=1)
def load_country_profiles(path: str | None = None) -> dict[str, dict[str, Any]]:
    file_path = Path(path) if path else PROFILES_PATH
    with file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(code): dict(profile) for code, profile in data["countries"].items()}


def format_country_profile(
    country_code: str,
    channel: str | None = None,
    *,
    path: str | None = None,
) -> str:
    profiles = load_country_profiles(path)
    profile = profiles.get(country_code.upper())
    if profile is None:
        return message("country_profile_missing", channel, country_code=country_code)
    return message("country_profile_card", channel, **profile)
