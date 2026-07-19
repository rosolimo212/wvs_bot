# coding: utf-8
"""
Импорт данных legacy Telegram-бота (схема tl) в prod-таблицы wvs.

Legacy:
    user_id в ответах и событиях — числовой Telegram ID (строка).
    События в tl.wvs_events: user_id, event_type, parameters, insert_time.

Новая схема:
    users + events + user_answers + user_reviews.
    user_id = sha256("telegram:" + external_user_id).
"""

from __future__ import annotations

import ast
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.db import postgres_connection
from core.identity import make_user_id

LEGACY_CHANNEL = "telegram"
MAIN_ANSWER_COLUMNS = (
    "user_id",
    "user_name",
    "qv_id",
    "qv_number",
    "qv_text",
    "answer_text",
)
REVIEW_COLUMNS = MAIN_ANSWER_COLUMNS
EVENT_COLUMNS = ("user_id", "event_type", "parameters", "timestamp")

LEGACY_EVENT_MAP: dict[str, str | None] = {
    "main_menu": "main_menu_visit",
    "main_questionary": "main_questionary_start",
    "secondary_questionary": "secondary_questionary_start",
    "record_answer": "answer_sent",
    "questions_finished": None,
    "secondary_questions_finished": None,
    "find_country": "find_counry_start",
    "find_position": "find_own_place_start",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class LegacyImportStats:
    users_created: int = 0
    users_skipped: int = 0
    main_answers: int = 0
    reviews: int = 0
    events_imported: int = 0
    events_skipped: int = 0
    events_skipped_no_user: int = 0
    events_skipped_unmapped: int = 0


@dataclass
class LegacyUserRecord:
    legacy_user_id: str
    external_user_id: str
    user_id: str
    user_name: str
    registration_date: datetime
    last_active_at: datetime


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _normalize_legacy_user_id(raw: str) -> tuple[str, str]:
    """
    Возвращает (legacy_user_id, external_user_id).

    Если в CSV уже лежит sha256 user_id нового формата — external_id неизвестен,
    импорт пользователя для таких строк пропускается (answers/events не привязать).
    """
    legacy = str(raw).strip()
    if _SHA256_RE.fullmatch(legacy):
        return legacy, ""
    return legacy, legacy


def _is_placeholder_user_name(user_name: str, external_user_id: str) -> bool:
    """Пустое имя или numeric external_user_id, сохранённый вместо @username."""
    name = user_name.strip()
    if not name:
        return True
    ext = external_user_id.strip()
    return bool(ext) and name == ext


def _pick_user_name(
    current: str,
    candidate: str,
    *,
    external_user_id: str,
) -> str:
    """Предпочитает реальный user_name, а не numeric external_user_id."""
    cur = current.strip()
    cand = candidate.strip()
    cur_placeholder = _is_placeholder_user_name(cur, external_user_id)
    cand_placeholder = _is_placeholder_user_name(cand, external_user_id)
    if cand_placeholder:
        return cur
    if cur_placeholder:
        return cand
    if len(cand) > len(cur):
        return cand
    return cur


def map_legacy_user_id(legacy_user_id: str) -> str:
    """Новый PK users из legacy Telegram ID."""
    _, external = _normalize_legacy_user_id(legacy_user_id)
    if not external:
        return legacy_user_id
    return make_user_id(LEGACY_CHANNEL, external)


def _parse_event_parameters(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    parsed: Any
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return {"legacy_raw": text}
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        if not parsed:
            return None
        first = parsed[0]
        if isinstance(first, dict):
            return first
        return {"legacy_list": parsed}
    return {"legacy_value": parsed}


def map_legacy_event(event_type: str, parameters: dict[str, Any] | None) -> tuple[str | None, dict[str, Any] | None]:
    mapped = LEGACY_EVENT_MAP.get(event_type.strip())
    if mapped is None and event_type.strip() not in LEGACY_EVENT_MAP:
        return event_type.strip(), parameters
    if mapped is None:
        return None, None
    params = dict(parameters or {})
    if mapped == "answer_sent" and "qv_number" not in params and "qv_id" in params:
        params["qv_number"] = params["qv_id"]
    return mapped, params or None


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _allocate_internal_user_id(conn: Any, schema: str) -> int:
    table_name = f"{schema}.users"
    with conn.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (table_name, "internal_user_id"))
        seq_row = cur.fetchone()
        if seq_row is None or not seq_row[0]:
            raise RuntimeError(f"Не найден sequence для {table_name}.internal_user_id")
        cur.execute("SELECT nextval(%s)", (seq_row[0],))
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("postgres не вернул internal_user_id")
    return int(row[0])


def _collect_users_from_users_csv(
    rows: list[dict[str, str]],
) -> dict[str, LegacyUserRecord]:
    users: dict[str, LegacyUserRecord] = {}
    now = datetime.now()

    for row in rows:
        external_id = str(row.get("external_user_id", "")).strip()
        if not external_id:
            continue
        user_name = str(row.get("user_name", "")).strip()
        ts = (
            _parse_timestamp(
                row.get("registration_time")
                or row.get("registration_date")
                or row.get("insert_time")
            )
            or now
        )
        users[external_id] = LegacyUserRecord(
            legacy_user_id=external_id,
            external_user_id=external_id,
            user_id=make_user_id(LEGACY_CHANNEL, external_id),
            user_name=user_name,
            registration_date=ts,
            last_active_at=ts,
        )
    return users


def _merge_user_records(
    primary: dict[str, LegacyUserRecord],
    supplemental: dict[str, LegacyUserRecord],
) -> dict[str, LegacyUserRecord]:
    for key, record in supplemental.items():
        if key not in primary:
            primary[key] = record
            continue
        existing = primary[key]
        existing.user_name = _pick_user_name(
            existing.user_name,
            record.user_name,
            external_user_id=key,
        )
        if record.registration_date < existing.registration_date:
            existing.registration_date = record.registration_date
        if record.last_active_at > existing.last_active_at:
            existing.last_active_at = record.last_active_at
    return primary


def _collect_users_from_rows(
    *row_groups: list[dict[str, str]],
) -> dict[str, LegacyUserRecord]:
    users: dict[str, LegacyUserRecord] = {}
    now = datetime.now()

    for rows in row_groups:
        for row in rows:
            legacy_raw = str(row.get("user_id", "")).strip()
            if not legacy_raw:
                continue
            legacy_id, external_id = _normalize_legacy_user_id(legacy_raw)
            if not external_id:
                continue

            user_name = str(row.get("user_name", "")).strip()
            ts = _parse_timestamp(row.get("insert_time") or row.get("timestamp")) or now
            key = external_id
            mapped_user_id = make_user_id(LEGACY_CHANNEL, external_id)

            if key not in users:
                users[key] = LegacyUserRecord(
                    legacy_user_id=legacy_id,
                    external_user_id=external_id,
                    user_id=mapped_user_id,
                    user_name=user_name,
                    registration_date=ts,
                    last_active_at=ts,
                )
                continue

            record = users[key]
            record.user_name = _pick_user_name(
                record.user_name,
                user_name,
                external_user_id=external_id,
            )
            if ts < record.registration_date:
                record.registration_date = ts
            if ts > record.last_active_at:
                record.last_active_at = ts

    return users


def _load_user_maps_by_external_ids(
    conn: Any,
    schema: str,
    external_ids: set[str],
) -> tuple[dict[str, int], dict[str, str], dict[str, str]]:
    """
    Возвращает:
        internal_by_user[user_id]
        external_by_user[user_id]
        user_id_by_external[external_user_id] — предпочитает registration_channel=telegram
    """
    internal_by_user: dict[str, int] = {}
    external_by_user: dict[str, str] = {}
    user_id_by_external: dict[str, str] = {}
    channel_by_external: dict[str, str] = {}

    if not external_ids:
        return internal_by_user, external_by_user, user_id_by_external

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT user_id, internal_user_id, external_user_id, registration_channel
            FROM {schema}.users
            WHERE external_user_id = ANY(%s)
            """,
            (sorted(external_ids),),
        )
        for user_id, internal_user_id, external_user_id, registration_channel in cur.fetchall():
            uid = str(user_id)
            ext = str(external_user_id)
            channel = str(registration_channel)
            internal_by_user[uid] = int(internal_user_id)
            external_by_user[uid] = ext
            prev_channel = channel_by_external.get(ext)
            if ext not in user_id_by_external or (
                prev_channel != LEGACY_CHANNEL and channel == LEGACY_CHANNEL
            ):
                user_id_by_external[ext] = uid
                channel_by_external[ext] = channel

    return internal_by_user, external_by_user, user_id_by_external


def _import_events(
    conn: Any,
    schema: str,
    event_rows: list[dict[str, str]],
    user_id_map: dict[str, str],
    stats: LegacyImportStats,
) -> None:
    external_ids = {
        str(row.get("user_id", "")).strip()
        for row in event_rows
        if str(row.get("user_id", "")).strip()
    }
    internal_by_user, external_by_user, user_id_by_external = _load_user_maps_by_external_ids(
        conn,
        schema,
        external_ids,
    )

    with conn.cursor() as cur:
        for row in event_rows:
            legacy_raw = str(row.get("user_id", "")).strip()
            if not legacy_raw:
                stats.events_skipped += 1
                stats.events_skipped_no_user += 1
                continue

            new_user_id = user_id_by_external.get(legacy_raw)
            if not new_user_id:
                new_user_id = user_id_map.get(legacy_raw) or map_legacy_user_id(legacy_raw)
            if new_user_id not in internal_by_user:
                stats.events_skipped += 1
                stats.events_skipped_no_user += 1
                continue

            event_name, params = map_legacy_event(
                str(row.get("event_type", "")),
                _parse_event_parameters(row.get("parameters")),
            )
            if not event_name:
                stats.events_skipped += 1
                stats.events_skipped_unmapped += 1
                continue

            event_time = (
                _parse_timestamp(row.get("timestamp") or row.get("insert_time"))
                or datetime.now()
            )
            cur.execute(
                f"""
                INSERT INTO {schema}.events (
                    timestamp, user_id, internal_user_id, external_user_id,
                    event_name, channel, event_parameters
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_time,
                    new_user_id,
                    internal_by_user[new_user_id],
                    external_by_user[new_user_id],
                    event_name,
                    LEGACY_CHANNEL,
                    json.dumps(params, ensure_ascii=False) if params is not None else None,
                ),
            )
            stats.events_imported += 1


def import_legacy_bot(
    logging_config: dict[str, Any],
    *,
    users_csv: Path | None = None,
    main_answers_csv: Path,
    reviews_csv: Path,
    events_csv: Path,
    dry_run: bool = False,
    events_only: bool = False,
) -> LegacyImportStats:
    schema = logging_config["schema"]
    user_rows = _read_csv_rows(users_csv) if users_csv else []
    main_rows = _read_csv_rows(main_answers_csv) if not events_only else []
    review_rows = _read_csv_rows(reviews_csv) if not events_only else []
    event_rows = _read_csv_rows(events_csv)

    users = _collect_users_from_users_csv(user_rows)
    if not events_only:
        users = _merge_user_records(
            users,
            _collect_users_from_rows(main_rows, review_rows, event_rows),
        )
    stats = LegacyImportStats()

    if dry_run:
        stats.users_created = len(users) if not events_only else 0
        stats.main_answers = len(main_rows)
        stats.reviews = len(review_rows)
        for row in event_rows:
            event_name, _ = map_legacy_event(
                str(row.get("event_type", "")),
                _parse_event_parameters(row.get("parameters")),
            )
            if event_name:
                stats.events_imported += 1
            else:
                stats.events_skipped += 1
                stats.events_skipped_unmapped += 1
        return stats

    user_id_map: dict[str, str] = {}
    for record in users.values():
        user_id_map[record.legacy_user_id] = record.user_id
        user_id_map[record.external_user_id] = record.user_id

    with postgres_connection(logging_config) as conn:
        if not events_only:
            existing: set[str] = set()
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT external_user_id
                    FROM {schema}.users
                    WHERE registration_channel = %s
                    """,
                    (LEGACY_CHANNEL,),
                )
                existing = {str(row[0]) for row in cur.fetchall()}

            for record in users.values():
                if record.external_user_id in existing:
                    with conn.cursor() as cur:
                        cur.execute(
                            f"""
                            UPDATE {schema}.users
                            SET user_name = %s
                            WHERE external_user_id = %s
                              AND registration_channel = %s
                              AND (
                                  trim(coalesce(user_name, '')) = ''
                                  OR user_name = external_user_id
                              )
                            """,
                            (
                                record.user_name,
                                record.external_user_id,
                                LEGACY_CHANNEL,
                            ),
                        )
                    stats.users_skipped += 1
                    continue
                internal_user_id = _allocate_internal_user_id(conn, schema)
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.users (
                            user_id, internal_user_id, external_user_id, user_name,
                            registration_date, registration_channel, last_active_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO NOTHING
                        """,
                        (
                            record.user_id,
                            internal_user_id,
                            record.external_user_id,
                            record.user_name,
                            record.registration_date,
                            LEGACY_CHANNEL,
                            record.last_active_at,
                        ),
                    )
                    if cur.rowcount:
                        stats.users_created += 1
                    else:
                        stats.users_skipped += 1

            def _resolve_user_id(raw: str) -> str | None:
                legacy_raw = str(raw).strip()
                if not legacy_raw:
                    return None
                if legacy_raw in user_id_map:
                    return user_id_map[legacy_raw]
                mapped = map_legacy_user_id(legacy_raw)
                if _SHA256_RE.fullmatch(legacy_raw):
                    return mapped if mapped else None
                return mapped

            user_name_by_user_id = {
                record.user_id: record.user_name for record in users.values()
            }

            def _insert_answers(rows: list[dict[str, str]], table: str) -> int:
                inserted = 0
                with conn.cursor() as cur:
                    for row in rows:
                        new_user_id = _resolve_user_id(str(row.get("user_id", "")))
                        if not new_user_id:
                            continue
                        qv_number = int(str(row.get("qv_number", "0")).strip() or 0)
                        if qv_number <= 0:
                            continue
                        insert_time = _parse_timestamp(row.get("insert_time")) or datetime.now()
                        row_user_name = str(row.get("user_name", "")).strip()
                        external_id = str(row.get("user_id", "")).strip()
                        answer_user_name = _pick_user_name(
                            user_name_by_user_id.get(new_user_id, ""),
                            row_user_name,
                            external_user_id=external_id,
                        )
                        cur.execute(
                            f"""
                            INSERT INTO {schema}.{table}
                                (user_id, user_name, qv_id, qv_number, qv_text, answer_text, insert_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (user_id, qv_number) DO UPDATE SET
                                user_name = EXCLUDED.user_name,
                                qv_id = EXCLUDED.qv_id,
                                qv_text = EXCLUDED.qv_text,
                                answer_text = EXCLUDED.answer_text,
                                insert_time = EXCLUDED.insert_time
                            """,
                            (
                                new_user_id,
                                answer_user_name,
                                str(row.get("qv_id", "")).strip(),
                                qv_number,
                                str(row.get("qv_text", "")).strip(),
                                str(row.get("answer_text", "")).strip(),
                                insert_time,
                            ),
                        )
                        inserted += 1
                return inserted

            stats.main_answers = _insert_answers(main_rows, "user_answers")
            stats.reviews = _insert_answers(review_rows, "user_reviews")

        _import_events(conn, schema, event_rows, user_id_map, stats)

    return stats


def _normalize_usernames(usernames: list[str]) -> set[str]:
    return {name.strip().lower() for name in usernames if name.strip()}


def _row_matches_usernames(row: dict[str, str], names: set[str]) -> bool:
    user_name = str(row.get("user_name", "")).strip().lower()
    return user_name in names


def filter_legacy_csv_rows(
    usernames: list[str],
    *,
    users_csv: Path | None,
    main_answers_csv: Path,
    reviews_csv: Path,
    events_csv: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Оставляет в CSV только строки выбранных user_name (без учёта регистра)."""
    names = _normalize_usernames(usernames)
    if not names:
        return [], [], [], []

    user_rows = _read_csv_rows(users_csv) if users_csv and users_csv.is_file() else []
    main_rows = [row for row in _read_csv_rows(main_answers_csv) if _row_matches_usernames(row, names)]
    review_rows = [row for row in _read_csv_rows(reviews_csv) if _row_matches_usernames(row, names)]
    user_rows = [row for row in user_rows if _row_matches_usernames(row, names)]

    legacy_ids: set[str] = set()
    for row in (*main_rows, *review_rows, *user_rows):
        uid = str(row.get("user_id", "")).strip()
        if uid:
            legacy_ids.add(uid)
    for row in user_rows:
        ext = str(row.get("external_user_id", "")).strip()
        if ext:
            legacy_ids.add(ext)

    event_rows = [
        row
        for row in _read_csv_rows(events_csv)
        if str(row.get("user_id", "")).strip() in legacy_ids
    ]
    return user_rows, main_rows, review_rows, event_rows


def import_legacy_from_csv_by_usernames(
    logging_config: dict[str, Any],
    usernames: list[str],
    *,
    users_csv: Path | None,
    main_answers_csv: Path,
    reviews_csv: Path,
    events_csv: Path,
    dry_run: bool = False,
) -> LegacyImportStats:
    """Импорт выбранных legacy-пользователей из CSV (scripts/migrate_legacy)."""
    import tempfile

    user_rows, main_rows, review_rows, event_rows = filter_legacy_csv_rows(
        usernames,
        users_csv=users_csv,
        main_answers_csv=main_answers_csv,
        reviews_csv=reviews_csv,
        events_csv=events_csv,
    )
    if not user_rows and not main_rows and not review_rows:
        return LegacyImportStats()

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        users_path = root / "users.csv"
        main_path = root / "user_answers.csv"
        reviews_path = root / "user_reviews.csv"
        events_path = root / "events.csv"

        if user_rows:
            _write_csv_rows(
                users_path,
                ["external_user_id", "user_name", "registration_time"],
                user_rows,
            )
        _write_csv_rows(main_path, list(MAIN_ANSWER_COLUMNS), main_rows)
        _write_csv_rows(reviews_path, list(REVIEW_COLUMNS), review_rows)
        _write_csv_rows(events_path, list(EVENT_COLUMNS), event_rows)

        return import_legacy_bot(
            logging_config,
            users_csv=users_path if user_rows else None,
            main_answers_csv=main_path,
            reviews_csv=reviews_path,
            events_csv=events_path,
            dry_run=dry_run,
        )


def _write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def fetch_legacy_rows_by_usernames(
    logging_config: dict[str, Any],
    usernames: list[str],
    *,
    legacy_schema: str = "tl",
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """
  Загружает строки из legacy-схемы tl по user_name (без учёта регистра).

  :return: (users_rows, main_answers, reviews, events)
    """
    names = sorted({name.strip().lower() for name in usernames if name.strip()})
    if not names:
        return [], [], [], []

    with postgres_connection(logging_config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT DISTINCT user_id::text, user_name
                FROM {legacy_schema}.user_answers
                WHERE lower(trim(user_name)) = ANY(%s)
                """,
                (names,),
            )
            legacy_users = cur.fetchall()

            if not legacy_users:
                cur.execute(
                    f"""
                    SELECT DISTINCT user_id::text, user_name
                    FROM {legacy_schema}.user_reviews
                    WHERE lower(trim(user_name)) = ANY(%s)
                    """,
                    (names,),
                )
                legacy_users = cur.fetchall()

            legacy_ids = [str(row[0]) for row in legacy_users]
            if not legacy_ids:
                return [], [], [], []

            cur.execute(
                f"""
                SELECT user_id::text, user_name, qv_id, qv_number::text, qv_text, answer_text,
                       insert_time::text
                FROM {legacy_schema}.user_answers
                WHERE user_id::text = ANY(%s)
                ORDER BY user_id, qv_number
                """,
                (legacy_ids,),
            )
            main_rows = [
                {
                    "user_id": str(row[0]),
                    "user_name": str(row[1] or ""),
                    "qv_id": str(row[2] or ""),
                    "qv_number": str(row[3] or ""),
                    "qv_text": str(row[4] or ""),
                    "answer_text": str(row[5] or ""),
                    "insert_time": str(row[6] or ""),
                }
                for row in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT user_id::text, user_name, qv_id, qv_number::text, qv_text, answer_text,
                       insert_time::text
                FROM {legacy_schema}.user_reviews
                WHERE user_id::text = ANY(%s)
                ORDER BY user_id, qv_number
                """,
                (legacy_ids,),
            )
            review_rows = [
                {
                    "user_id": str(row[0]),
                    "user_name": str(row[1] or ""),
                    "qv_id": str(row[2] or ""),
                    "qv_number": str(row[3] or ""),
                    "qv_text": str(row[4] or ""),
                    "answer_text": str(row[5] or ""),
                    "insert_time": str(row[6] or ""),
                }
                for row in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT user_id::text, event_type, parameters::text, insert_time::text
                FROM {legacy_schema}.wvs_events
                WHERE user_id::text = ANY(%s)
                ORDER BY insert_time
                """,
                (legacy_ids,),
            )
            event_rows = [
                {
                    "user_id": str(row[0]),
                    "event_type": str(row[1] or ""),
                    "parameters": str(row[2] or ""),
                    "timestamp": str(row[3] or ""),
                }
                for row in cur.fetchall()
            ]

    users_rows = [
        {
            "external_user_id": str(row[0]),
            "user_name": str(row[1] or row[0]),
            "registration_time": "",
        }
        for row in legacy_users
    ]
    return users_rows, main_rows, review_rows, event_rows


def import_legacy_from_tl_by_usernames(
    logging_config: dict[str, Any],
    usernames: list[str],
    *,
    legacy_schema: str = "tl",
    dry_run: bool = False,
) -> LegacyImportStats:
    """Импорт выбранных legacy-пользователей напрямую из схемы tl."""
    import tempfile

    users_rows, main_rows, review_rows, event_rows = fetch_legacy_rows_by_usernames(
        logging_config,
        usernames,
        legacy_schema=legacy_schema,
    )
    if not users_rows and not main_rows:
        return LegacyImportStats()

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        users_csv = root / "users.csv"
        main_csv = root / "user_answers.csv"
        reviews_csv = root / "user_reviews.csv"
        events_csv = root / "events.csv"

        _write_csv_rows(
            users_csv,
            ["external_user_id", "user_name", "registration_time"],
            users_rows,
        )
        _write_csv_rows(main_csv, list(MAIN_ANSWER_COLUMNS), main_rows)
        _write_csv_rows(reviews_csv, list(REVIEW_COLUMNS), review_rows)
        _write_csv_rows(events_csv, list(EVENT_COLUMNS), event_rows)

        return import_legacy_bot(
            logging_config,
            users_csv=users_csv,
            main_answers_csv=main_csv,
            reviews_csv=reviews_csv,
            events_csv=events_csv,
            dry_run=dry_run,
        )
