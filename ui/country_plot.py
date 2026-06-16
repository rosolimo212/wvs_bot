# coding: utf-8
"""График положения пользователя относительно стран."""

from __future__ import annotations

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
) -> plt.Figure | None:
    df = load_country_data(logging_config, reference_schema=reference_schema)
    if df is None or df.empty:
        return None

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
    return fig
