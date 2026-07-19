# coding: utf-8
"""Человекочитаемые названия каналов в отчётах."""

from __future__ import annotations

CHANNEL_REPORT_LABELS: dict[str, str] = {
    "streamlit": "браузер",
    "telegram": "телега",
    "console": "консоль",
}


def channel_report_label(channel: str) -> str:
    key = str(channel or "").strip()
    return CHANNEL_REPORT_LABELS.get(key, key or "неизвестно")
