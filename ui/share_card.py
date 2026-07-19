# coding: utf-8
"""
PNG-карточка результата «Найти страну» для скачивания в Streamlit.

Содержимое:
    RV/SV, matplotlib-карта стран, краткий профиль страны, QR на лендинг.

Важно:
    Генерация тяжёлая (SQL + seaborn) — вызывать только по кнопке «Подготовить»,
    кэшировать bytes в session_state, не пересобирать на каждом rerun.
"""

from __future__ import annotations

import io
import textwrap
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from core.analytics.index_interpretation import describe_rv_score, describe_sv_score
from core.country_profiles import load_country_profiles
from ui.country_plot import build_country_plot
from ui.mini_qr import qr_to_rgb

DEFAULT_LANDING_URL = "https://worldvaluessurveybot.info"

_BG = "#102a43"
_PANEL = "#f0f4f8"
_INK = "#102a43"
_MUTED = "#486581"
_ACCENT = "#0c6b58"


def _country_fact_lines(country_code: str) -> list[str]:
    profile = load_country_profiles().get(country_code.upper())
    if not profile:
        return [f"Страна: {country_code.upper()}", "Расширенный профиль пока недоступен."]
    lines = [str(profile.get("full_name") or country_code.upper())]
    gov = profile.get("government_type")
    if gov:
        lines.append(f"Форма правления: {gov}")
    gdp = profile.get("gdp_per_capita_usd")
    if gdp is not None:
        try:
            lines.append(f"ВВП на душу: ${int(gdp):,}")
        except (TypeError, ValueError):
            lines.append(f"ВВП на душу: {gdp}")
    pop = profile.get("population")
    if pop is not None:
        try:
            lines.append(f"Население: {int(pop):,}")
        except (TypeError, ValueError):
            lines.append(f"Население: {pop}")
    flight = profile.get("flight_hours_from_london")
    if flight is not None:
        lines.append(f"Перелёт из Лондона: ~{flight} ч")
    return lines


def _qr_array(url: str):
    return qr_to_rgb(url, box_size=6, border=2)


def build_country_share_png(
    *,
    user_rv: float,
    user_sv: float,
    country_code: str,
    country_rv: float | None = None,
    country_sv: float | None = None,
    logging_config: dict[str, Any] | None = None,
    reference_schema: str = "wvs",
    landing_url: str = DEFAULT_LANDING_URL,
    country_df: Any = None,
) -> bytes:
    """
    Собирает одну PNG: заголовок, карта стран, факты о стране, QR на лендинг.

    :raises RuntimeError: если нет logging_config или не удалось построить график
    """
    if logging_config is None:
        raise RuntimeError("Для карточки со графиком нужен logging_config")

    plot_fig, _timings = build_country_plot(
        float(user_sv),
        float(user_rv),
        logging_config,
        reference_schema=reference_schema,
        country_df=country_df,
    )
    if plot_fig is None:
        raise RuntimeError("Не удалось построить график стран для карточки")

    plot_buf = io.BytesIO()
    plot_fig.savefig(plot_buf, format="png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(plot_fig)
    plot_buf.seek(0)
    plot_img = plt.imread(plot_buf, format="png")

    code = str(country_code).upper()
    fact_lines = _country_fact_lines(code)
    if country_rv is not None and country_sv is not None:
        fact_lines.append(f"Индексы страны: RV {float(country_rv):.1f}, SV {float(country_sv):.1f}")

    fig = plt.figure(figsize=(11.5, 14.5), dpi=120)
    fig.patch.set_facecolor(_BG)
    gs = GridSpec(
        4,
        2,
        figure=fig,
        height_ratios=[0.55, 3.2, 1.6, 0.9],
        width_ratios=[1.15, 0.85],
        hspace=0.28,
        wspace=0.18,
        left=0.06,
        right=0.94,
        top=0.95,
        bottom=0.05,
    )

    ax_title = fig.add_subplot(gs[0, :])
    ax_title.set_facecolor(_PANEL)
    ax_title.set_xlim(0, 1)
    ax_title.set_ylim(0, 1)
    ax_title.axis("off")
    ax_title.text(0.03, 0.72, "World Values Survey · бот", fontsize=11, color=_MUTED)
    ax_title.text(0.03, 0.38, "Мой результат: ближайшая страна", fontsize=18, color=_INK, fontweight="bold")
    ax_title.text(
        0.03,
        0.08,
        f"RV {float(user_rv):.0f}   ·   SV {float(user_sv):.0f}   ·   {code}",
        fontsize=14,
        color=_ACCENT,
        fontweight="bold",
    )

    ax_plot = fig.add_subplot(gs[1, :])
    ax_plot.imshow(plot_img)
    ax_plot.axis("off")
    ax_plot.set_facecolor(_PANEL)

    ax_facts = fig.add_subplot(gs[2, 0])
    ax_facts.set_facecolor(_PANEL)
    ax_facts.set_xlim(0, 1)
    ax_facts.set_ylim(0, 1)
    ax_facts.axis("off")
    y = 0.92
    ax_facts.text(0.04, y, "О стране", fontsize=13, color=_ACCENT, fontweight="bold")
    y -= 0.14
    for line in fact_lines:
        wrapped = textwrap.fill(str(line), width=42)
        ax_facts.text(0.04, y, wrapped, fontsize=10, color=_INK, va="top", linespacing=1.25)
        y -= 0.045 * (wrapped.count("\n") + 1) + 0.02
        if y < 0.08:
            break
    y = min(y, 0.35)
    ax_facts.text(0.04, y, textwrap.fill(describe_rv_score(float(user_rv)), 42), fontsize=9, color=_MUTED, va="top")
    y -= 0.18
    if y > 0.05:
        ax_facts.text(0.04, y, textwrap.fill(describe_sv_score(float(user_sv)), 42), fontsize=9, color=_MUTED, va="top")

    ax_qr = fig.add_subplot(gs[2, 1])
    ax_qr.set_facecolor(_PANEL)
    ax_qr.imshow(_qr_array(landing_url))
    ax_qr.axis("off")
    ax_qr.set_title("Пройти самому", fontsize=11, color=_INK, pad=8)

    ax_footer = fig.add_subplot(gs[3, :])
    ax_footer.set_facecolor(_PANEL)
    ax_footer.set_xlim(0, 1)
    ax_footer.set_ylim(0, 1)
    ax_footer.axis("off")
    ax_footer.text(0.03, 0.55, landing_url, fontsize=12, color=_ACCENT, fontweight="bold")
    ax_footer.text(0.03, 0.2, "Отсканируйте QR или откройте ссылку", fontsize=10, color=_MUTED)

    out = io.BytesIO()
    fig.savefig(out, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out.getvalue()


def build_own_place_share_png(
    *,
    user_rv: float,
    user_sv: float,
    country_name: str = "",
    landing_url: str = DEFAULT_LANDING_URL,
) -> bytes:
    """Лёгкая карточка «своё место»: индексы + QR (без тяжёлых гистограмм)."""
    fig = plt.figure(figsize=(8.5, 10), dpi=120)
    fig.patch.set_facecolor(_BG)
    gs = GridSpec(3, 1, figure=fig, height_ratios=[1.2, 2.2, 1.4], hspace=0.25, left=0.08, right=0.92, top=0.94, bottom=0.06)

    ax_t = fig.add_subplot(gs[0])
    ax_t.set_facecolor(_PANEL)
    ax_t.axis("off")
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(0, 1)
    ax_t.text(0.05, 0.7, "World Values Survey · бот", fontsize=11, color=_MUTED)
    ax_t.text(0.05, 0.35, "Моё место в социуме", fontsize=18, color=_INK, fontweight="bold")
    ax_t.text(0.05, 0.08, f"RV {float(user_rv):.0f}   ·   SV {float(user_sv):.0f}", fontsize=14, color=_ACCENT, fontweight="bold")

    ax_b = fig.add_subplot(gs[1])
    ax_b.set_facecolor(_PANEL)
    ax_b.axis("off")
    ax_b.set_xlim(0, 1)
    ax_b.set_ylim(0, 1)
    y = 0.9
    for block in (describe_rv_score(float(user_rv)), describe_sv_score(float(user_sv))):
        wrapped = textwrap.fill(block, 50)
        ax_b.text(0.05, y, wrapped, fontsize=12, color=_INK, va="top", linespacing=1.35)
        y -= 0.05 * (wrapped.count("\n") + 1) + 0.08
    if country_name.strip():
        ax_b.text(0.05, max(y, 0.1), f"Выборка: {country_name.strip()}", fontsize=11, color=_MUTED)

    ax_q = fig.add_subplot(gs[2])
    ax_q.set_facecolor(_PANEL)
    ax_q.imshow(_qr_array(landing_url))
    ax_q.axis("off")
    ax_q.set_title(landing_url, fontsize=11, color=_ACCENT, pad=6)

    out = io.BytesIO()
    fig.savefig(out, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out.getvalue()
