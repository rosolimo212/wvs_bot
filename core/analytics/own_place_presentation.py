# coding: utf-8
"""Текст и meta для экрана «Понять своё место в социуме»."""

from __future__ import annotations

from typing import Any

from core.analytics.index_interpretation import (
    describe_rv_score,
    describe_sv_score,
    rv_comparison_percent,
    sv_comparison_percent,
)
from core.analytics.position import (
    BotComparisonResult,
    GenderAgePeerSample,
    OwnPlaceContext,
    OwnPlaceResult,
    UserPosition,
)
from core.analytics.secondary_profile import SecondaryProfile
from core.messages import message

SV_INDEX_TITLE = "Ценности выживания / самовыражения"
RV_INDEX_TITLE = "Традиционные / секулярно-рациональные ценности"
SV_AXIS_LABEL = "Индекс выживания / самовыражения"
RV_AXIS_LABEL = "Индекс традиционных / секулярно-рациональных ценностей"


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


def _sv_lead_in(sv: float, channel: str | None) -> str:
    if sv < 10:
        return message("find_own_place_sv_lead_survival", channel)
    if sv < 14:
        return message("find_own_place_sv_lead_balance", channel)
    return message("find_own_place_sv_lead_self_expression", channel)


def _rv_lead_in(rv: float, channel: str | None) -> str:
    if rv < 13:
        return message("find_own_place_rv_lead_traditional", channel)
    if rv < 16:
        return message("find_own_place_rv_lead_balance", channel)
    return message("find_own_place_rv_lead_secular", channel)


def _comparison_bullets(
    *,
    channel: str | None,
    country_name: str,
    global_pos: UserPosition,
    gender_age_pos: UserPosition | None,
    bot: BotComparisonResult | None,
    index_kind: str,
    user_value: float,
) -> list[str]:
    bullets: list[str] = []

    if index_kind == "sv":
        percent = sv_comparison_percent(user_value, global_pos.sv_rank)
        bullets.append(
            message(
                "find_own_place_compare_wvs_country",
                channel,
                percent=percent,
                country_name=country_name,
            )
        )
        if gender_age_pos is not None:
            peer_percent = sv_comparison_percent(user_value, gender_age_pos.sv_rank)
            bullets.append(
                message(
                    "find_own_place_compare_wvs_peers",
                    channel,
                    percent=peer_percent,
                    country_name=country_name,
                )
            )
        if bot is not None and bot.gender_age_pos is not None:
            bot_percent = sv_comparison_percent(user_value, bot.gender_age_pos.sv_rank)
            bullets.append(
                message(
                    "find_own_place_compare_bot_peers",
                    channel,
                    percent=bot_percent,
                    country_name=country_name,
                )
            )
        return bullets

    percent = rv_comparison_percent(user_value, global_pos.rv_rank)
    bullets.append(
        message(
            "find_own_place_compare_wvs_country",
            channel,
            percent=percent,
            country_name=country_name,
        )
    )
    if gender_age_pos is not None:
        peer_percent = rv_comparison_percent(user_value, gender_age_pos.rv_rank)
        bullets.append(
            message(
                "find_own_place_compare_wvs_peers",
                channel,
                percent=peer_percent,
                country_name=country_name,
            )
        )
    if bot is not None and bot.gender_age_pos is not None:
        bot_percent = rv_comparison_percent(user_value, bot.gender_age_pos.rv_rank)
        bullets.append(
            message(
                "find_own_place_compare_bot_peers",
                channel,
                percent=bot_percent,
                country_name=country_name,
            )
        )
    return bullets


def _compact_index_section(
    *,
    index_kind: str,
    user_value: float,
    own_place: OwnPlaceResult,
    peers: GenderAgePeerSample | None,
    channel: str | None,
) -> tuple[list[str], dict[str, Any] | None]:
    ctx = own_place.context
    index_name = SV_INDEX_TITLE if index_kind == "sv" else RV_INDEX_TITLE
    describe = describe_sv_score if index_kind == "sv" else describe_rv_score
    lead_in = _sv_lead_in if index_kind == "sv" else _rv_lead_in

    lines = [
        message(
            "find_own_place_index_value",
            channel,
            index_name=index_name,
            value=user_value,
        ),
        describe(user_value),
        lead_in(user_value, channel) + ":",
        *_comparison_bullets(
            channel=channel,
            country_name=ctx.country_name,
            global_pos=own_place.global_pos,
            gender_age_pos=own_place.gender_age_pos,
            bot=own_place.bot,
            index_kind=index_kind,
            user_value=user_value,
        ),
    ]

    chart = None
    if peers is not None:
        if index_kind == "sv":
            chart = _chart_meta(
                kind="sv",
                user_value=float(user_value),
                peer_values=list(peers.sv_values),
                title=SV_INDEX_TITLE,
                x_label=SV_AXIS_LABEL,
            )
        else:
            chart = _chart_meta(
                kind="rv",
                user_value=float(user_value),
                peer_values=list(peers.rv_values),
                title=RV_INDEX_TITLE,
                x_label=RV_AXIS_LABEL,
            )

    return lines, chart


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

    peers = own_place.gender_age_peers
    charts: list[dict[str, Any]] = []

    if own_place.global_pos is not None:
        parts.append(message("find_own_place_intro", channel))

        sv_lines, sv_chart = _compact_index_section(
            index_kind="sv",
            user_value=float(user_sv),
            own_place=own_place,
            peers=peers,
            channel=channel,
        )
        parts.append("\n".join(sv_lines))
        if sv_chart is not None:
            charts.append(sv_chart)

        rv_lines, rv_chart = _compact_index_section(
            index_kind="rv",
            user_value=float(user_rv),
            own_place=own_place,
            peers=peers,
            channel=channel,
        )
        parts.append("\n".join(rv_lines))
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
