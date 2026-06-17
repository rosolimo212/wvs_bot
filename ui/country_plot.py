# coding: utf-8
"""График положения пользователя относительно стран."""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from core.analytics.sql import fetch_all_rows

ANNOTATE_COUNTRIES = [
    "RUS",
    "USA",
    "UZB",
    "GTM",
    "AND",
    "PAK",
    "IRN",
    "ARM",
    "KOR",
    "DEU",
    "JPN",
    "MDV",
    "ARG",
    "CAN",
]


@dataclass(frozen=True)
class CountryPlotTimings:
    sql_ms: int
    processing_ms: int
    render_ms: int
    total_ms: int


@dataclass(frozen=True)
class CountryPlotPipelineTimings:
    sql_ms: int
    processing_ms: int
    render_ms: int
    country_plot_loaded_ms: int
    total_ms: int


def format_country_plot_timings(timings: CountryPlotPipelineTimings) -> str:
    """Текстовый отчёт по этапам загрузки карты стран."""
    return "\n".join(
        [
            "Загрузка карты стран:",
            f"  1. SQL (country_data)      {timings.sql_ms:>5} ms",
            f"  2. Построение графика      {timings.processing_ms:>5} ms",
            f"  3. Отрисовка (pyplot)      {timings.render_ms:>5} ms",
            f"  4. Карточка страны         {timings.country_plot_loaded_ms:>5} ms",
            f"  ─────────────────────────────────",
            f"  Итого                      {timings.total_ms:>5} ms",
        ]
    )


def load_country_data(
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "tl",
) -> pd.DataFrame | None:
    schema = reference_schema
    query = f"""
        SELECT country_code, country_rv, country_sv, cluster
        FROM {schema}.country_data
        WHERE country_code != 'EGY'
    """
    try:
        rows = fetch_all_rows(query, logging_config)
    except Exception:
        return None
    if not rows:
        return None
    return pd.DataFrame(rows, columns=["country_code", "country_rv", "country_sv", "cluster"])


def build_country_plot(
    user_sv: float,
    user_rv: float,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "tl",
    country_df: pd.DataFrame | None = None,
) -> tuple[plt.Figure | None, CountryPlotTimings]:
    started = time.perf_counter()

    sql_started = time.perf_counter()
    if country_df is not None:
        df = country_df
    else:
        df = load_country_data(logging_config, reference_schema=reference_schema)
    sql_ms = int((time.perf_counter() - sql_started) * 1000)
    if df is None or df.empty:
        total_ms = int((time.perf_counter() - started) * 1000)
        return None, CountryPlotTimings(sql_ms=sql_ms, processing_ms=0, render_ms=0, total_ms=total_ms)

    processing_started = time.perf_counter()
    df = df.copy()
    df["country_rv"] = df["country_rv"].fillna(user_rv).astype(float)
    df["country_sv"] = df["country_sv"].fillna(user_sv).astype(float)
    df["cluster"] = df["cluster"].astype("category")

    n_colors = len(df["cluster"].cat.categories)
    palette = sns.color_palette("tab10" if n_colors <= 10 else "husl", n_colors=n_colors)

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.scatterplot(
        data=df,
        x="country_sv",
        y="country_rv",
        hue="cluster",
        palette=palette,
        s=80,
        edgecolor="k",
        alpha=0.9,
        ax=ax,
    )

    bbox = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.35)
    for _, row in df[df["country_code"].isin(ANNOTATE_COUNTRIES)].iterrows():
        ax.text(
            row["country_sv"],
            row["country_rv"] + 0.02,
            str(row["country_code"]),
            fontsize=9,
            fontweight="bold",
            ha="left",
            va="bottom",
            bbox=bbox,
        )

    ax.axvline(float(user_sv), color="red", linestyle="--", linewidth=1.5, zorder=200, label="Вы")
    ax.axhline(float(user_rv), color="red", linestyle="--", linewidth=1.5, zorder=200)
    ax.set_title("Положение относительно других стран", fontsize=14)
    ax.set_xlabel("Традиционные/Секулярно-рациональные ценности")
    ax.set_ylabel("Ценности выживания/Самовыражения")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    processing_ms = int((time.perf_counter() - processing_started) * 1000)
    total_ms = int((time.perf_counter() - started) * 1000)
    return fig, CountryPlotTimings(
        sql_ms=sql_ms,
        processing_ms=processing_ms,
        render_ms=0,
        total_ms=total_ms,
    )


def measure_country_plot_pipeline(
    user_sv: float,
    user_rv: float,
    country_code: str,
    logging_config: dict[str, Any],
    *,
    reference_schema: str = "tl",
    country_df: pd.DataFrame | None = None,
    channel: str = "streamlit",
) -> CountryPlotPipelineTimings:
    """Замер всех этапов загрузки карты (для диагностики и pre-commit)."""
    from core.country_profiles import format_country_profile

    total_started = time.perf_counter()
    fig, build_timings = build_country_plot(
        user_sv,
        user_rv,
        logging_config,
        reference_schema=reference_schema,
        country_df=country_df,
    )

    render_ms = 0
    country_plot_loaded_ms = 0
    if fig is not None:
        render_started = time.perf_counter()
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png")
        plt.close(fig)
        render_ms = int((time.perf_counter() - render_started) * 1000)

        profile_started = time.perf_counter()
        format_country_profile(country_code, channel)
        country_plot_loaded_ms = int((time.perf_counter() - profile_started) * 1000)

    total_ms = int((time.perf_counter() - total_started) * 1000)
    return CountryPlotPipelineTimings(
        sql_ms=build_timings.sql_ms,
        processing_ms=build_timings.processing_ms,
        render_ms=render_ms,
        country_plot_loaded_ms=country_plot_loaded_ms,
        total_ms=total_ms,
    )
