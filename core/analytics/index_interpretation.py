# coding: utf-8
"""
Краткие пояснения к индексам RV и SV.

Цель:
    Человекочитаемые описания индексов и формулировки сравнения с выборкой.

Вход:
    Числовые RV/SV, rank (0–100), название страны, channel.

Выход:
    Строки для экранов «найти страну», «понять своё место», завершение анкеты.
"""

from __future__ import annotations


def describe_rv_score(rv: float) -> str:
    """Пояснение к индексу традиционных/секулярно-рациональных ценностей."""
    if rv < 13:
        return (
            "Скорее всего, у вас ярко выражены уважение к авторитетам, "
            "для вас важны семейные отношения и стабильность."
        )
    if rv < 16:
        return "Для вас в равной мере важны традиционные и секулярно-рациональные ценности."
    return (
        "Скорее всего, у вас в приоритете научные знания, технический прогресс "
        "и уважение к индивидуальности."
    )


def describe_sv_score(sv: float) -> str:
    """Пояснение к индексу выживания/самовыражения."""
    if sv < 10:
        return "Скорее всего, у вас в приоритете материальная и физическая безопасность."
    if sv < 14:
        return "Для вас в равной мере важны ценности выживания и самовыражения."
    return (
        "Скорее всего, у вас в приоритете самореализация, доверие "
        "и участие в общественной жизни."
    )


def format_indices_summary(rv: float, sv: float) -> str:
    """Блок с числами и пояснениями сразу после расчёта индексов."""
    return "\n".join(
        [
            f"Ваш индекс традиционных/секулярно-рациональных ценностей составляет {rv}",
            describe_rv_score(rv),
            "",
            f"Ваш индекс ценностей выживания/самовыражения составляет {sv}",
            describe_sv_score(sv),
        ]
    )


def _comparison_percent(rank: int, *, high_pole: bool) -> int:
    rank = max(0, min(100, int(rank)))
    return rank if high_pole else 100 - rank


def sv_comparison_percent(sv: float, rank: int) -> int:
    if sv < 10:
        return _comparison_percent(rank, high_pole=False)
    return _comparison_percent(rank, high_pole=True)


def rv_comparison_percent(rv: float, rank: int) -> int:
    if rv < 13:
        return _comparison_percent(rank, high_pole=False)
    return _comparison_percent(rank, high_pole=True)


def format_rv_peer_comparison(
    rv: float,
    rank: int,
    country_name: str,
    *,
    peers_label: str = "участников опросов WVS",
) -> str:
    """Сравнение RV с выборкой в человекочитаемой формулировке."""
    if rv < 13:
        pct = _comparison_percent(rank, high_pole=False)
        return (
            f"Вам ближе традиционные ценности, чем {pct}% {peers_label} "
            f"из dfitq cnhfys ({country_name})."
        )
    if rv < 16:
        pct = _comparison_percent(rank, high_pole=True)
        return (
            f"Для вас в равной мере важны традиционные и секулярно-рациональные ценности; "
            f"этот индекс у вас выше, чем у {pct}% {peers_label} из вашей страны ({country_name})."
        )
    pct = _comparison_percent(rank, high_pole=True)
    return (
        f"Вам ближе секулярно-рациональные ценности, чем {pct}% {peers_label} "
        f"из вашей страны ({country_name})."
    )


def format_sv_peer_comparison(
    sv: float,
    rank: int,
    country_name: str,
    *,
    peers_label: str = "участников опросов",
) -> str:
    """Сравнение SV с выборкой в человекочитаемой формулировке."""
    if sv < 10:
        pct = _comparison_percent(rank, high_pole=False)
        return (
            f"Вам ближе ценности выживания, чем {pct}% {peers_label} "
            f"из вашей страны ({country_name})."
        )
    if sv < 14:
        pct = _comparison_percent(rank, high_pole=True)
        return (
            f"Для вас в равной мере важны ценности выживания и самовыражения; "
            f"этот индекс у вас выше, чем у {pct}% {peers_label} из вашей страны ({country_name})."
        )
    pct = _comparison_percent(rank, high_pole=True)
    return (
        f"Вам ближе ценности самовыражения, чем {pct}% {peers_label} "
        f"из вашей страны ({country_name})."
    )
