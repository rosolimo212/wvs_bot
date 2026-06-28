# coding: utf-8
"""
Данные респондента из дополнительной анкеты.

Цель:
    Извлечь birth_year, country_text, gender, age из user_reviews.

Вход:
    Список ответов {qv_id, answer_text}.

Выход:
    SecondaryProfile с флагом has_demographics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

PREFER_NOT = "предпочитаю не отвечать"


@dataclass(frozen=True)
class SecondaryProfile:
    birth_year: int | None
    country_text: str | None
    gender: str | None

    @property
    def age(self) -> int | None:
        if self.birth_year is None:
            return None
        return datetime.now().year - self.birth_year

    @property
    def has_demographics(self) -> bool:
        return self.age is not None and bool(self.gender)


def _clean_answer(text: str) -> str | None:
    value = text.strip()
    if not value or value.casefold() == PREFER_NOT:
        return None
    return value


def parse_secondary_profile(answers: list[dict[str, Any]]) -> SecondaryProfile:
    by_id = {str(row["qv_id"]): str(row["answer_text"]) for row in answers}
    birth_raw = _clean_answer(by_id.get("S01", ""))
    country_raw = _clean_answer(by_id.get("S02", ""))
    gender_raw = _clean_answer(by_id.get("S03", ""))

    birth_year = None
    if birth_raw is not None:
        try:
            birth_year = int(birth_raw)
        except ValueError:
            birth_year = None

    return SecondaryProfile(
        birth_year=birth_year,
        country_text=country_raw,
        gender=gender_raw,
    )
