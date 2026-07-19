# coding: utf-8
"""Расписание daily-отчёта по config (timezone + send_at)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_SEND_AT = "11:04"
DEFAULT_TIMEZONE = "Europe/Moscow"


def parse_send_at(value: str | None) -> tuple[int, int]:
    """'HH:MM' → (hour, minute)."""
    text = (value or DEFAULT_SEND_AT).strip()
    try:
        hour_s, minute_s = text.split(":", 1)
        hour = int(hour_s)
        minute = int(minute_s)
    except ValueError as exc:
        raise ValueError(f"send_at должен быть в формате HH:MM, получено {value!r}") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"send_at вне диапазона суток: {value!r}")
    return hour, minute


def resolve_timezone(name: str | None) -> ZoneInfo:
    return ZoneInfo((name or DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE)


def is_send_at_now(
    *,
    send_at: str | None,
    timezone: str | None,
    now: datetime | None = None,
) -> bool:
    tz = resolve_timezone(timezone)
    moment = now.astimezone(tz) if now is not None else datetime.now(tz)
    hour, minute = parse_send_at(send_at)
    return moment.hour == hour and moment.minute == minute


def default_sent_marker_path(project_root: Path | None = None) -> Path:
    root = project_root or Path(__file__).resolve().parents[2]
    return root / ".cache" / "daily_audience_last_sent_date"


def read_sent_date(marker_path: Path) -> date | None:
    if not marker_path.is_file():
        return None
    text = marker_path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return date.fromisoformat(text)


def write_sent_date(marker_path: Path, day: date) -> None:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(day.isoformat() + "\n", encoding="utf-8")


def already_sent_today(
    marker_path: Path,
    *,
    timezone: str | None,
    now: datetime | None = None,
) -> bool:
    tz = resolve_timezone(timezone)
    moment = now.astimezone(tz) if now is not None else datetime.now(tz)
    sent = read_sent_date(marker_path)
    return sent == moment.date()
