from __future__ import annotations

import json
from pathlib import Path

from core.migration.legacy_import import (
    map_legacy_event,
    map_legacy_user_id,
    _parse_event_parameters,
    import_legacy_bot,
)


def test_map_legacy_user_id_from_telegram() -> None:
    mapped = map_legacy_user_id("123456789")
    assert mapped != "123456789"
    assert len(mapped) == 64


def test_map_legacy_user_id_keeps_sha256() -> None:
    existing = "a" * 64
    assert map_legacy_user_id(existing) == existing


def test_parse_event_parameters_list() -> None:
    params = _parse_event_parameters(json.dumps([{"qv_number": 3}]))
    assert params == {"qv_number": 3}


def test_map_legacy_event_record_answer() -> None:
    name, params = map_legacy_event("record_answer", {"qv_number": 1})
    assert name == "answer_sent"
    assert params == {"qv_number": 1}


def test_map_legacy_event_skips_finished() -> None:
    name, params = map_legacy_event("questions_finished", {})
    assert name is None
    assert params is None


def test_import_legacy_dry_run(tmp_path: Path) -> None:
    main_csv = tmp_path / "main.csv"
    reviews_csv = tmp_path / "reviews.csv"
    events_csv = tmp_path / "events.csv"
    main_csv.write_text(
        "user_id,user_name,qv_id,qv_number,qv_text,answer_text,insert_time\n"
        "111,alice,Q173,1,text,1. Да,2024-01-01 10:00:00\n",
        encoding="utf-8",
    )
    reviews_csv.write_text(
        "user_id,user_name,qv_id,qv_number,qv_text,answer_text,insert_time\n"
        "111,alice,S02,2,text,Россия,2024-01-01 10:05:00\n",
        encoding="utf-8",
    )
    events_csv.write_text(
        "user_id,event_type,parameters,timestamp\n"
        '111,main_menu,{},2024-01-01 09:00:00\n'
        '111,questions_finished,{},2024-01-01 11:00:00\n',
        encoding="utf-8",
    )
    stats = import_legacy_bot(
        {"schema": "wvs"},
        main_answers_csv=main_csv,
        reviews_csv=reviews_csv,
        events_csv=events_csv,
        dry_run=True,
    )
    assert stats.users_created == 1
    assert stats.main_answers == 1
    assert stats.reviews == 1
    assert stats.events_imported == 1
    assert stats.events_skipped == 1
