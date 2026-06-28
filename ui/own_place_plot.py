# coding: utf-8
"""Гистограммы для экрана «Понять своё место в социуме»."""

from __future__ import annotations

import io
from typing import Any

import matplotlib.pyplot as plt
import plotly.graph_objects as go


def _histogram_bins(peer_values: list[float], user_value: float) -> list[int]:
    low = int(min(peer_values + [user_value]))
    high = int(max(peer_values + [user_value]))
    return list(range(low, high + 2))


def build_index_histogram_plotly(
    peer_values: list[float],
    user_value: float,
    *,
    title: str,
    x_label: str,
) -> go.Figure | None:
    if not peer_values:
        return None
    bins = _histogram_bins(peer_values, user_value)
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=peer_values,
            xbins=dict(start=bins[0], end=bins[-1], size=1),
            name="Участники опроса",
            marker_color="#64748b",
            opacity=0.85,
        )
    )
    fig.add_vline(
        x=float(user_value),
        line_width=2.5,
        line_color="#dc2626",
        annotation_text="Вы",
        annotation_position="top",
    )
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="Число людей",
        bargap=0.05,
        height=420,
        showlegend=False,
    )
    return fig


def build_index_histogram_matplotlib(
    peer_values: list[float],
    user_value: float,
    *,
    title: str,
    x_label: str,
) -> plt.Figure | None:
    if not peer_values:
        return None
    bins = _histogram_bins(peer_values, user_value)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.hist(peer_values, bins=bins, color="#64748b", edgecolor="white", alpha=0.9)
    ax.axvline(float(user_value), color="#dc2626", linewidth=2.5, label="Вы")
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel("Число людей")
    ax.legend()
    fig.tight_layout()
    return fig


def export_index_histogram_png(
    peer_values: list[float],
    user_value: float,
    *,
    title: str,
    x_label: str,
) -> bytes | None:
    fig = build_index_histogram_matplotlib(
        peer_values,
        user_value,
        title=title,
        x_label=x_label,
    )
    if fig is None:
        return None
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()
