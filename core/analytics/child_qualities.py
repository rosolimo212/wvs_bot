# coding: utf-8
"""Сопоставление свободного текста с качествами WVS (Q11, Q17)."""

from __future__ import annotations

import re
import unicodedata

_WORD_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)


def normalize_match_text(text: str) -> str:
    """Приводит текст к виду для поиска: регистр, «ё», пробелы."""
    normalized = unicodedata.normalize("NFKC", text.strip())
    normalized = normalized.casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", normalized)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _max_typo_distance(word: str) -> int:
    length = len(word)
    if length >= 9:
        return 2
    if length >= 5:
        return 1
    return 0


def _contains_stem(text: str, stems: tuple[str, ...]) -> bool:
    return any(stem in text for stem in stems)


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _fuzzy_word_match(text: str, canonical_words: tuple[str, ...]) -> bool:
    for word in _WORD_SPLIT_RE.split(text):
        if len(word) < 4:
            continue
        max_dist = _max_typo_distance(word)
        if max_dist == 0:
            continue
        for target in canonical_words:
            if word == target:
                return True
            if abs(len(word) - len(target)) > max_dist:
                continue
            if _levenshtein(word, target) <= max_dist:
                return True
    return False


# Q17 — Obedience / послушание (1 = упомянуто, 2 = не упомянуто).
_OBEDIENCE_STEMS = (
    "послуш",
    "obedien",
    "poslush",
    "poslushen",
)
_OBEDIENCE_PHRASES = (
    "исполнительность",
    "подчинение",
)
_OBEDIENCE_WORDS = (
    "послушание",
    "послушность",
    "послушливость",
    "obedience",
    "poslushanie",
    "poslushenie",
)

# Q11 — Imagination / воображение.
_IMAGINATION_STEMS = (
    "воображ",
    "imagin",
    "фантаз",
    "fantasy",
    "fantasi",
    "креатив",
    "creativ",
)
_IMAGINATION_PHRASES = (
    "творческое мышление",
    "творческий подход",
    "творчество",
    "образность",
    "выдумка",
)
_IMAGINATION_WORDS = (
    "воображение",
    "воображения",
    "фантазия",
    "фантазии",
    "фантазирование",
    "imagination",
    "imaginative",
    "креативность",
    "creativity",
    "fantasy",
    "fantasia",
    "vooobrazhenie",
    "voobrazhenie",
)


def text_mentions_obedience(answer_text: str) -> bool:
    """True, если в ответе упомянуто послушание (с учётом опечаток и синонимов)."""
    text = normalize_match_text(answer_text)
    if not text or text in {"не знаю", "-1. не знаю"}:
        return False
    return (
        _contains_stem(text, _OBEDIENCE_STEMS)
        or _contains_phrase(text, _OBEDIENCE_PHRASES)
        or _fuzzy_word_match(text, _OBEDIENCE_WORDS)
    )


def text_mentions_imagination(answer_text: str) -> bool:
    """True, если в ответе упомянуто воображение (с учётом опечаток и синонимов)."""
    text = normalize_match_text(answer_text)
    if not text or text in {"не знаю", "-1. не знаю"}:
        return False
    return (
        _contains_stem(text, _IMAGINATION_STEMS)
        or _contains_phrase(text, _IMAGINATION_PHRASES)
        or _fuzzy_word_match(text, _IMAGINATION_WORDS)
    )
