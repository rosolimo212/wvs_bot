from __future__ import annotations

from core.analytics.own_place_presentation import build_own_place_presentation
from core.analytics.position import (
    GenderAgePeerSample,
    OwnPlaceContext,
    OwnPlaceResult,
    UserPosition,
)
from core.analytics.secondary_profile import SecondaryProfile


def _sample_own_place() -> OwnPlaceResult:
    peers = GenderAgePeerSample(
        sv_values=tuple(float(i) for i in range(8, 18)),
        rv_values=tuple(float(i) for i in range(10, 20)),
        sv_rank=60,
        rv_rank=55,
        age_window=3,
        sample_size=40,
        gender_label="женщин",
    )
    return OwnPlaceResult(
        global_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=55, sv_rank=60),
        context=OwnPlaceContext(
            country_code="RUS",
            country_name="Россия",
            used_default_country=False,
            user_country_missing_in_sample=False,
            age_window=3,
            age_sample_size=40,
            age_sample_too_small=False,
        ),
        age_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=50, sv_rank=60),
        gender_age_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=55, sv_rank=60),
        gender_age_peers=peers,
        bot=None,
    )


def test_own_place_presentation_sv_before_rv() -> None:
    text, meta = build_own_place_presentation(
        user_rv=18.0,
        user_sv=16.0,
        own_place=_sample_own_place(),
        profile=SecondaryProfile(1990, "Россия", "Женщина"),
        channel=None,
        unknown_count=0,
        warn_inaccurate=False,
    )
    sv_pos = text.index("Ценности выживания")
    rv_pos = text.index("Традиционные")
    assert sv_pos < rv_pos
    assert "составляет 16" in text
    assert "составляет 18" in text
    assert "самовыражения" in text
    assert meta.get("show_own_place_charts") is True
    assert len(meta["own_place_charts"]) == 2
    assert meta["own_place_charts"][0]["kind"] == "sv"
    assert meta["own_place_charts"][1]["kind"] == "rv"


def test_own_place_presentation_no_duplicate_full_indices() -> None:
    text, _ = build_own_place_presentation(
        user_rv=18.0,
        user_sv=16.0,
        own_place=_sample_own_place(),
        profile=SecondaryProfile(1990, "Россия", "Женщина"),
        channel=None,
        unknown_count=0,
        warn_inaccurate=False,
    )
    assert text.count("составляет") == 2
