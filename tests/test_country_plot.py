from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from ui.country_plot import (
    CountryPlotPipelineTimings,
    build_country_plot,
    format_country_plot_timings,
    measure_country_plot_pipeline,
)


SAMPLE_COUNTRY_DATA = pd.DataFrame(
    [
        {"country_code": "RUS", "country_rv": 10.0, "country_sv": 12.0, "cluster": 1},
        {"country_code": "USA", "country_rv": 11.0, "country_sv": 13.0, "cluster": 2},
    ]
)


def test_build_country_plot_returns_timings() -> None:
    fig, timings = build_country_plot(
        12.0,
        10.0,
        {"schema": "wvs"},
        country_df=SAMPLE_COUNTRY_DATA,
    )

    assert fig is not None
    assert timings.sql_ms >= 0
    assert timings.processing_ms >= 0
    assert timings.total_ms >= timings.processing_ms
    plt.close(fig)


def test_format_country_plot_timings() -> None:
    report = format_country_plot_timings(
        CountryPlotPipelineTimings(
            sql_ms=10,
            processing_ms=80,
            render_ms=20,
            country_plot_loaded_ms=5,
            total_ms=115,
        )
    )
    assert "SQL (country_data)" in report
    assert "Построение графика" in report
    assert "Отрисовка (pyplot)" in report
    assert "Карточка страны" in report
    assert "Итого" in report
    assert "115 ms" in report


def test_measure_country_plot_pipeline() -> None:
    timings = measure_country_plot_pipeline(
        12.0,
        10.0,
        "RUS",
        {"schema": "wvs"},
        country_df=SAMPLE_COUNTRY_DATA,
    )
    assert timings.sql_ms >= 0
    assert timings.processing_ms >= 0
    assert timings.render_ms >= 0
    assert timings.country_plot_loaded_ms >= 0
    assert timings.total_ms >= timings.processing_ms
