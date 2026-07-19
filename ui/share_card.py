# coding: utf-8
"""
PNG-карточка результата для скачивания / репоста (Streamlit).

Цель:
    Одна картинка с RV/SV и кратким итогом + ссылками на продукт.
    Без зависимостей соцсетей — только matplotlib (уже в requirements).

Выход:
    bytes PNG.
"""

from __future__ import annotations

import io
import textwrap
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from core.analytics.index_interpretation import describe_rv_score, describe_sv_score

# Спокойная палитра (не purple / не cream+terracotta).
_BG = "#0f2744"
_CARD = "#f4f7fb"
_INK = "#15202b"
_MUTED = "#5a6b7d"
_ACCENT = "#1f7a6c"
_CTA = "#0f2744"

DEFAULT_LANDING_URL = "https://worldvaluessurveybot.info"
DEFAULT_BOT_URL = "https://t.me/values_counter_bot"


def _wrap(text: str, width: int = 52) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) if text else ""


def build_country_share_png(
    *,
    user_rv: float,
    user_sv: float,
    country_code: str,
    country_rv: float | None = None,
    country_sv: float | None = None,
    landing_url: str = DEFAULT_LANDING_URL,
    bot_url: str = DEFAULT_BOT_URL,
) -> bytes:
    """Карточка «Найти страну»."""
    lines = [
        ("brand", "World Values Survey · бот"),
        ("title", "Мои индексы ценностей"),
        ("metric", f"RV  {user_rv:.0f}    ·    SV  {user_sv:.0f}"),
        ("body", describe_rv_score(float(user_rv))),
        ("body", describe_sv_score(float(user_sv))),
        ("gap", ""),
        ("subtitle", "Ближайшая страна"),
        ("accent", str(country_code).upper()),
    ]
    if country_rv is not None and country_sv is not None:
        lines.append(("muted", f"у жителей страны: RV {country_rv:.1f}, SV {country_sv:.1f}"))
    lines.extend(
        [
            ("gap", ""),
            ("cta", "Пройти самому:"),
            ("link", landing_url),
            ("link", bot_url),
        ]
    )
    return _render_card(lines, filename_hint="country")


def build_own_place_share_png(
    *,
    user_rv: float,
    user_sv: float,
    country_name: str = "",
    landing_url: str = DEFAULT_LANDING_URL,
    bot_url: str = DEFAULT_BOT_URL,
) -> bytes:
    """Карточка «Понять своё место»."""
    lines = [
        ("brand", "World Values Survey · бот"),
        ("title", "Моё место в социуме"),
        ("metric", f"RV  {user_rv:.0f}    ·    SV  {user_sv:.0f}"),
        ("body", describe_rv_score(float(user_rv))),
        ("body", describe_sv_score(float(user_sv))),
    ]
    if country_name.strip():
        lines.append(("muted", f"Сравнение с выборкой: {country_name.strip()}"))
    lines.extend(
        [
            ("gap", ""),
            ("cta", "Пройти самому:"),
            ("link", landing_url),
            ("link", bot_url),
        ]
    )
    return _render_card(lines, filename_hint="own_place")


def build_share_png_from_meta(
    *,
    kind: str,
    meta: dict[str, Any],
    landing_url: str = DEFAULT_LANDING_URL,
    bot_url: str = DEFAULT_BOT_URL,
) -> bytes | None:
    """
    Собирает PNG из meta экрана Streamlit.

    kind: \"country\" | \"own_place\"
    """
    try:
        user_rv = float(meta["user_rv"])
        user_sv = float(meta["user_sv"])
    except (KeyError, TypeError, ValueError):
        return None

    if kind == "country":
        code = str(meta.get("country_code") or "").strip()
        if not code:
            return None
        country_rv = meta.get("country_rv")
        country_sv = meta.get("country_sv")
        return build_country_share_png(
            user_rv=user_rv,
            user_sv=user_sv,
            country_code=code,
            country_rv=float(country_rv) if country_rv is not None else None,
            country_sv=float(country_sv) if country_sv is not None else None,
            landing_url=landing_url,
            bot_url=bot_url,
        )
    if kind == "own_place":
        return build_own_place_share_png(
            user_rv=user_rv,
            user_sv=user_sv,
            country_name=str(meta.get("country_name") or ""),
            landing_url=landing_url,
            bot_url=bot_url,
        )
    return None


def _render_card(lines: list[tuple[str, str]], *, filename_hint: str) -> bytes:
    _ = filename_hint
    fig_w, fig_h = 8.0, 10.0
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor(_BG)

    card = FancyBboxPatch(
        (0.06, 0.06),
        0.88,
        0.88,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=0,
        facecolor=_CARD,
        transform=ax.transAxes,
        zorder=0,
    )
    ax.add_patch(card)

    y = 0.88
    for kind, text in lines:
        if kind == "gap":
            y -= 0.03
            continue
        if kind == "brand":
            ax.text(0.12, y, text, fontsize=11, color=_MUTED, fontfamily="DejaVu Sans", transform=ax.transAxes)
            y -= 0.045
        elif kind == "title":
            ax.text(
                0.12,
                y,
                text,
                fontsize=22,
                color=_INK,
                fontweight="bold",
                fontfamily="DejaVu Sans",
                transform=ax.transAxes,
            )
            y -= 0.07
        elif kind == "metric":
            ax.text(
                0.12,
                y,
                text,
                fontsize=20,
                color=_ACCENT,
                fontweight="bold",
                fontfamily="DejaVu Sans",
                transform=ax.transAxes,
            )
            y -= 0.055
        elif kind == "subtitle":
            ax.text(0.12, y, text, fontsize=12, color=_MUTED, fontfamily="DejaVu Sans", transform=ax.transAxes)
            y -= 0.04
        elif kind == "accent":
            ax.text(
                0.12,
                y,
                text,
                fontsize=28,
                color=_ACCENT,
                fontweight="bold",
                fontfamily="DejaVu Sans",
                transform=ax.transAxes,
            )
            y -= 0.06
        elif kind == "body":
            wrapped = _wrap(text, 46)
            ax.text(
                0.12,
                y,
                wrapped,
                fontsize=12,
                color=_INK,
                fontfamily="DejaVu Sans",
                va="top",
                transform=ax.transAxes,
                linespacing=1.35,
            )
            y -= 0.028 * (wrapped.count("\n") + 1) + 0.025
        elif kind == "muted":
            ax.text(0.12, y, text, fontsize=11, color=_MUTED, fontfamily="DejaVu Sans", transform=ax.transAxes)
            y -= 0.04
        elif kind == "cta":
            ax.text(0.12, y, text, fontsize=12, color=_CTA, fontweight="bold", fontfamily="DejaVu Sans", transform=ax.transAxes)
            y -= 0.04
        elif kind == "link":
            ax.text(0.12, y, text, fontsize=11, color=_ACCENT, fontfamily="DejaVu Sans", transform=ax.transAxes)
            y -= 0.035

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()
