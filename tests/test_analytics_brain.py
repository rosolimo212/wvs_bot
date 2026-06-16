from __future__ import annotations

from core.brain import on_find_country, on_find_own_place
from core.models import Screen


def test_on_find_country_formats_result() -> None:
    response = on_find_country(
        rv=10,
        sv=12,
        country_code="FIN",
        country_rv=9.5,
        country_sv=11.2,
        channel="streamlit",
    )
    assert response.screen == Screen.FIND_COUNTRY
    assert "FIN" in response.text
    assert response.meta["show_country_plot"] is True


def test_on_find_own_place_joins_parts() -> None:
    response = on_find_own_place("Часть 1\n\nЧасть 2", channel="streamlit")
    assert response.screen == Screen.FIND_OWN_PLACE
    assert "Часть 1" in response.text
