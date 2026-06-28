# coding: utf-8
"""Текст и meta для экрана «Понять своё место в социуме»."""

from __future__ import annotations

from typing import Any

from core.analytics.index_interpretation import (
    describe_rv_score,
    describe_sv_score,
    format_rv_peer_comparison,
    format_sv_peer_comparison,
)
from core.analytics.position import GenderAgePeerSample, OwnPlaceContext, OwnPlaceResult
from core.analytics.secondary_profile import SecondaryProfile
from core.messages import message

SV_INDEX_TITLE = "Ценности выживания / самовыражения"
RV_INDEX_TITLE = "Традиционные / секулярно-рациональные ценности"
SV_AXIS_LABEL = "Индекс выживания / самовыражения"
RV_AXIS_LABEL = "Индекс традиционных / секулярно-рациональных ценностей"


def _peer_heading(
    channel: str | None,
    *,
    country_name: str,
    gender_label: str,
    age_window: int,
    sample_size: int,
) -> str:
    return message(
        "find_own_place_peer_heading",
        channel,
        country_name=country_name,
        gender_label=gender_label,
        age_window=age_window,
        sample_size=sample_size,
    )


def _chart_meta(
    *,
    kind: str,
    user_value: float,
    peer_values: list[float],
    title: str,
    x_label: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "user_value": user_value,
        "peer_values": peer_values,
        "title": title,
        "x_label": x_label,
    }


def _sv_section(
    user_sv: float,
    peers: GenderAgePeerSample,
    ctx: OwnPlaceContext,
    channel: str | None,
) -> tuple[list[str], dict[str, Any] | None]:
    parts = [
        message("find_own_place_sv_title", channel),
        message(
            "find_own_place_index_value",
            channel,
            index_name=SV_INDEX_TITLE,
            value=user_sv,
        ),
        describe_sv_score(user_sv),
        _peer_heading(
            channel,
            country_name=ctx.country_name,
            gender_label=peers.gender_label,
            age_window=peers.age_window,
            sample_size=peers.sample_size,
        ),
        format_sv_peer_comparison(
            user_sv,
            peers.sv_rank,
            ctx.country_name,
            peers_label=f"{peers.gender_label} вашего возраста",
        ),
    ]
    chart = _chart_meta(
        kind="sv",
        user_value=float(user_sv),
        peer_values=list(peers.sv_values),
        title=SV_INDEX_TITLE,
        x_label=SV_AXIS_LABEL,
    )
    return parts, chart


def _rv_section(
    user_rv: float,
    peers: GenderAgePeerSample,
    ctx: OwnPlaceContext,
    channel: str | None,
) -> tuple[list[str], dict[str, Any] | None]:
    parts = [
        message("find_own_place_rv_title", channel),
        message(
            "find_own_place_index_value",
            channel,
            index_name=RV_INDEX_TITLE,
            value=user_rv,
        ),
        describe_rv_score(user_rv),
        _peer_heading(
            channel,
            country_name=ctx.country_name,
            gender_label=peers.gender_label,
            age_window=peers.age_window,
            sample_size=peers.sample_size,
        ),
        format_rv_peer_comparison(
            user_rv,
            peers.rv_rank,
            ctx.country_name,
            peers_label=f"{peers.gender_label} вашего возраста",
        ),
    ]
    chart = _chart_meta(
        kind="rv",
        user_value=float(user_rv),
        peer_values=list(peers.rv_values),
        title=RV_INDEX_TITLE,
        x_label=RV_AXIS_LABEL,
    )
    return parts, chart


def build_own_place_presentation(
    *,
    user_rv: float,
    user_sv: float,
    own_place: OwnPlaceResult,
    profile: SecondaryProfile,
    channel: str | None,
    unknown_count: int,
    warn_inaccurate: bool,
) -> tuple[str, dict[str, Any]]:
    ctx = own_place.context
    parts: list[str] = []

    if warn_inaccurate:
        parts.append(message("main_questionary_indices_inaccurate_warning", channel))

    if ctx.user_country_missing_in_sample:
        parts.append(
            message(
                "find_own_place_country_missing",
                channel,
                country_text=profile.country_text or "",
            )
        )
    elif ctx.used_default_country and not profile.country_text:
        parts.append(message("find_own_place_country_default", channel))

    charts: list[dict[str, Any]] = []
    peers = own_place.gender_age_peers

    if peers is not None:
        sv_parts, sv_chart = _sv_section(user_sv, peers, ctx, channel)
        parts.extend(sv_parts)
        if sv_chart is not None:
            charts.append(sv_chart)

        rv_parts, rv_chart = _rv_section(user_rv, peers, ctx, channel)
        parts.extend(rv_parts)
        if rv_chart is not None:
            charts.append(rv_chart)
    elif profile.age is not None and ctx.age_sample_too_small:
        parts.append(
            message(
                "find_own_place_age_sample_small",
                channel,
                country_name=ctx.country_name,
                age_window=ctx.age_window or 0,
                sample_size=ctx.age_sample_size or 0,
            )
        )
    else:
        parts.append(message("find_own_place_secondary_hint", channel))

    meta: dict[str, Any] = {}
    if charts:
        meta["show_own_place_charts"] = True
        meta["own_place_charts"] = charts

    return "\n\n".join(parts), meta
