# coding: utf-8
"""Загрузка шаблонов исходящих коммуникаций."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_MESSAGES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "communication_messages.json"
)

# В JSON ключ browser соответствует registration_channel=streamlit.
_CHANNEL_TO_JSON_KEY = {
    "telegram": "telegram",
    "streamlit": "browser",
    "console": "console",
}


@dataclass(frozen=True)
class CommunicationTemplate:
    template_id: str
    when: str
    default: str
    by_channel: dict[str, str]


@lru_cache(maxsize=4)
def _load_raw(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("communication_messages.json должен быть объектом")
    templates = data.get("templates")
    if not isinstance(templates, dict):
        raise ValueError("В communication_messages.json нужна секция templates")
    return templates


def clear_messages_cache() -> None:
    _load_raw.cache_clear()


def load_template(
    template_id: str,
    *,
    path: Path | None = None,
) -> CommunicationTemplate:
    file_path = path or DEFAULT_MESSAGES_PATH
    templates = _load_raw(str(file_path))
    raw = templates.get(template_id)
    if not isinstance(raw, dict):
        known = ", ".join(sorted(templates)) or "(пусто)"
        raise KeyError(f"Шаблон {template_id!r} не найден. Известные: {known}")
    tid = str(raw.get("template_id") or template_id).strip()
    default = str(raw.get("default") or "").strip()
    if not default:
        raise ValueError(f"У шаблона {template_id!r} пустой default")
    by_channel: dict[str, str] = {}
    for key in ("telegram", "browser", "console"):
        value = raw.get(key)
        if value is not None and str(value).strip():
            by_channel[key] = str(value)
    return CommunicationTemplate(
        template_id=tid,
        when=str(raw.get("when") or ""),
        default=default,
        by_channel=by_channel,
    )


def render_template_text(
    template: CommunicationTemplate,
    *,
    channel: str,
    user_name: str,
) -> str:
    json_key = _CHANNEL_TO_JSON_KEY.get(channel, channel)
    body = template.by_channel.get(json_key) or template.default
    return body.replace("{user_name}", user_name.strip() or "друг")


def list_template_ids(*, path: Path | None = None) -> list[str]:
    file_path = path or DEFAULT_MESSAGES_PATH
    return sorted(_load_raw(str(file_path)).keys())
