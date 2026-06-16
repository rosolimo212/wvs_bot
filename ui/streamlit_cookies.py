# coding: utf-8
"""
Долгоживущий external_user_id для Streamlit.

Читаем — st.context.cookies;
пишем — components.html + document.cookie.

В cookie храним ТОЛЬКО external_user_id (uuid).
Экран и имя — из postgres через handle_start.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from typing import Any

EXTERNAL_COOKIE_NAME = "wvs_external_id"
LEGACY_COOKIE_NAME = "wvs_browser_session"
COOKIE_MAX_AGE_SEC = 365 * 86400

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_external_id(value: str) -> bool:
    return bool(_UUID_RE.match(value.strip()))


def new_streamlit_external_id() -> str:
    return str(uuid.uuid4())


def _external_from_legacy_blob(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        raw = value.get("external_user_id")
        if raw and is_valid_external_id(str(raw)):
            return str(raw).strip()
        return None
    if not isinstance(value, str) or not value:
        return None

    parsed: Any = None
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
        parsed = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None

    if isinstance(parsed, dict):
        raw = parsed.get("external_user_id")
        if raw and is_valid_external_id(str(raw)):
            return str(raw).strip()
    return None


def read_external_id_from_cookies(cookies: Any) -> str | None:
    if cookies is None:
        return None

    direct = cookies.get(EXTERNAL_COOKIE_NAME)
    if direct and is_valid_external_id(str(direct)):
        return str(direct).strip()

    return _external_from_legacy_blob(cookies.get(LEGACY_COOKIE_NAME))


def persist_external_id_cookie(external_id: str) -> None:
    if not is_valid_external_id(external_id):
        return

    import streamlit.components.v1 as components

    safe = external_id.strip()
    components.html(
        f"""<script>
        document.cookie = "{EXTERNAL_COOKIE_NAME}={safe}; path=/; max-age={COOKIE_MAX_AGE_SEC}; SameSite=Lax";
        </script>""",
        height=0,
        width=0,
    )


def resolve_external_user_id(state: dict[str, Any], cookies: Any) -> str:
    from_cookie = read_external_id_from_cookies(cookies)
    if from_cookie:
        state["external_user_id"] = from_cookie
        return from_cookie

    existing = state.get("external_user_id")
    if existing and is_valid_external_id(str(existing)):
        return str(existing)

    new_id = new_streamlit_external_id()
    state["external_user_id"] = new_id
    return new_id
