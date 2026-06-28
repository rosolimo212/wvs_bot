# coding: utf-8
"""Краткие пояснения к индексам RV и SV."""

from __future__ import annotations


def describe_rv_score(rv: float) -> str:
    """Пояснение к индексу традиционных/секулярно-рациональных ценностей."""
    if rv < 13:
        return (
            "Скорее всего, у вас ярко выражены уважение к авторитетам, "
            "высокая ценность семьи и стабильности."
        )
    if rv < 16:
        return "У вас наблюдается баланс между традиционными и секулярно-рациональными ценностями."
    return (
        "Скорее всего, у вас в приоритете научные знания, технический прогресс "
        "и уважение к индивидуальности."
    )


def describe_sv_score(sv: float) -> str:
    """Пояснение к индексу выживания/самовыражения."""
    if sv < 10:
        return "Скорее всего, у вас в приоритете материальная и физическая безопасность."
    if sv < 14:
        return "У вас баланс между ценностями выживания и самовыражения."
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
    peers_label: str = "участников опросов",
) -> str:
    """Сравнение RV с выборкой в человекочитаемой формулировке."""
    if rv < 13:
        pct = _comparison_percent(rank, high_pole=False)
        return (
            f"Вам ближе традиционные ценности, чем у {pct}% {peers_label} "
            f"из {country_name}."
        )
    if rv < 16:
        pct = _comparison_percent(rank, high_pole=True)
        return (
            f"У вас баланс традиционных и секулярно-рациональных ценностей; "
            f"показатель выше, чем у {pct}% {peers_label} из {country_name}."
        )
    pct = _comparison_percent(rank, high_pole=True)
    return (
        f"Вам ближе секулярно-рациональные ценности, чем у {pct}% {peers_label} "
        f"из {country_name}."
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
            f"Вам ближе ценности выживания, чем у {pct}% {peers_label} "
            f"из {country_name}."
        )
    if sv < 14:
        pct = _comparison_percent(rank, high_pole=True)
        return (
            f"У вас баланс ценностей выживания и самовыражения; "
            f"показатель выше, чем у {pct}% {peers_label} из {country_name}."
        )
    pct = _comparison_percent(rank, high_pole=True)
    return (
        f"Вам ближе ценности самовыражения, чем у {pct}% {peers_label} "
        f"из {country_name}."
    )
