from __future__ import annotations

from ui.own_place_plot import (
    build_index_histogram_matplotlib,
    build_index_histogram_plotly,
    export_index_histogram_png,
)


def test_build_histogram_plotly() -> None:
    peers = [9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    fig = build_index_histogram_plotly(
        peers,
        16.0,
        title="SV",
        x_label="Индекс SV",
    )
    assert fig is not None


def test_export_histogram_png() -> None:
    png = export_index_histogram_png(
        [10.0, 11.0, 12.0, 13.0],
        14.0,
        title="RV",
        x_label="Индекс RV",
    )
    assert png is not None
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_build_histogram_matplotlib() -> None:
    fig = build_index_histogram_matplotlib(
        [10.0, 11.0, 12.0],
        11.5,
        title="RV",
        x_label="Индекс RV",
    )
    assert fig is not None
    import matplotlib.pyplot as plt

    plt.close(fig)
