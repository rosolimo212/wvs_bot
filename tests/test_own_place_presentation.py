from __future__ import annotations

from core.analytics.own_place_presentation import build_own_place_presentation
from core.analytics.position import (
    BotComparisonResult,
    GenderAgePeerSample,
    OwnPlaceContext,
    OwnPlaceResult,
    UserPosition,
)
from core.analytics.secondary_profile import SecondaryProfile
from core.messages import message


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


def test_own_place_presentation_compact_format() -> None:
    text, meta = build_own_place_presentation(
        user_rv=18.0,
        user_sv=16.0,
        own_place=_sample_own_place(),
        profile=SecondaryProfile(1990, "Россия", "Женщина"),
        channel=None,
        unknown_count=0,
        warn_inaccurate=False,
    )
    assert message("find_own_place_intro", None) in text
    sv_pos = text.index("Ценности выживания")
    rv_pos = text.index("Традиционные")
    assert sv_pos < rv_pos
    assert "составляет 16" in text
    assert "составляет 18" in text
    assert message("find_own_place_sv_lead_self_expression", None) + ":" in text
    assert message(
        "find_own_place_compare_wvs_country",
        None,
        percent=60,
        country_name="Россия",
    ) in text
    assert message(
        "find_own_place_compare_wvs_peers",
        None,
        percent=60,
        country_name="Россия",
    ) in text
    assert meta.get("show_own_place_charts") is True
    assert len(meta["own_place_charts"]) == 2


def test_own_place_presentation_includes_bot_bullet() -> None:
    own_place = _sample_own_place()
    own_place = OwnPlaceResult(
        global_pos=own_place.global_pos,
        context=own_place.context,
        age_pos=own_place.age_pos,
        gender_age_pos=own_place.gender_age_pos,
        gender_age_peers=own_place.gender_age_peers,
        bot=BotComparisonResult(
            global_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=70, sv_rank=65),
            age_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=60, sv_rank=55),
            gender_age_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=50, sv_rank=45),
            other_users_count=12,
            age_window=3,
            age_sample_size=4,
            age_sample_too_small=False,
            compare_pos=UserPosition(rv=18.0, sv=16.0, rv_rank=50, sv_rank=45),
            compare_scope="gender_age",
            compare_sample_size=4,
        ),
    )
    text, _ = build_own_place_presentation(
        user_rv=18.0,
        user_sv=16.0,
        own_place=own_place,
        profile=SecondaryProfile(1990, "Россия", "Женщина"),
        channel=None,
        unknown_count=0,
        warn_inaccurate=False,
    )
    assert message(
        "find_own_place_compare_bot_peers",
        None,
        percent=45,
        country_name="Россия",
    ) in text
    assert "12" not in text
