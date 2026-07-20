from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt

from ui.share_card import (
    build_country_share_png,
    build_own_place_share_png,
    plain_text,
)


def test_plain_text_strips_markdown() -> None:
    assert plain_text("**Россия**") == "Россия"


def test_own_place_share_png_is_png_bytes() -> None:
    charts = [
        {
            "peer_values": [10, 11, 12, 13, 14, 15],
            "user_value": 12.0,
            "title": "SV",
            "x_label": "SV",
        },
        {
            "peer_values": [8, 9, 10, 11, 12],
            "user_value": 10.0,
            "title": "RV",
            "x_label": "RV",
        },
    ]
    data = build_own_place_share_png(
        user_rv=18,
        user_sv=16,
        own_place_charts=charts,
        share_body_lines=["- 60% пользователей из России"],
    )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 5000


def test_country_share_png_embeds_plot() -> None:
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1])

    fake_df = MagicMock()
    with patch("ui.share_card.build_country_plot", return_value=(fig, MagicMock())):
        data = build_country_share_png(
            user_rv=15,
            user_sv=12,
            country_code="RUS",
            country_rv=14.0,
            country_sv=11.0,
            logging_config={"schema": "wvs"},
            country_df=fake_df,
        )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 5000


def test_country_share_requires_logging_config() -> None:
    try:
        build_country_share_png(
            user_rv=1,
            user_sv=1,
            country_code="RUS",
            logging_config=None,
        )
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "logging_config" in str(exc)


def test_share_png_has_alpha_channel() -> None:
    charts = [
        {
            "peer_values": [10, 11, 12, 13, 14, 15],
            "user_value": 12.0,
            "title": "SV",
            "x_label": "SV",
        },
    ]
    data = build_own_place_share_png(
        user_rv=10,
        user_sv=12,
        own_place_charts=charts,
        share_body_lines=["тест"],
    )
    img = plt.imread(io.BytesIO(data), format="png")
    assert img.shape[-1] == 4
