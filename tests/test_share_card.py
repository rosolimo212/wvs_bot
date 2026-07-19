from __future__ import annotations

from ui.share_card import (
    build_country_share_png,
    build_own_place_share_png,
    build_share_png_from_meta,
)


def test_country_share_png_is_png_bytes() -> None:
    data = build_country_share_png(
        user_rv=15,
        user_sv=12,
        country_code="RUS",
        country_rv=14.5,
        country_sv=11.2,
    )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 2000


def test_own_place_share_png_is_png_bytes() -> None:
    data = build_own_place_share_png(
        user_rv=18,
        user_sv=16,
        country_name="Россия",
    )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_share_png_from_meta_country() -> None:
    png = build_share_png_from_meta(
        kind="country",
        meta={
            "user_rv": 10,
            "user_sv": 11,
            "country_code": "USA",
            "country_rv": 12,
            "country_sv": 13,
        },
    )
    assert png is not None
    assert png.startswith(b"\x89PNG")


def test_share_png_from_meta_requires_fields() -> None:
    assert build_share_png_from_meta(kind="country", meta={"user_rv": 1}) is None
    assert build_share_png_from_meta(kind="own_place", meta={}) is None
