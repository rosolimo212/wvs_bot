from __future__ import annotations

import json
from pathlib import Path

from core.migration.legacy_import import (
    filter_legacy_csv_rows,
    map_legacy_event,
    map_legacy_user_id,
    _collect_users_from_rows,
    _collect_users_from_users_csv,
    _merge_user_records,
    _parse_event_parameters,
    _pick_user_name,
    import_legacy_bot,
    import_legacy_from_csv_by_usernames,
)


def test_pick_user_name_prefers_real_name_over_external_id() -> None:
    assert _pick_user_name("Rkhbvs", "309551566", external_user_id="309551566") == "Rkhbvs"
    assert _pick_user_name("309551566", "Rkhbvs", external_user_id="309551566") == "Rkhbvs"
    assert _pick_user_name("", "kirsl", external_user_id="109992493") == "kirsl"


def test_merge_user_records_keeps_csv_name_when_events_have_no_user_name() -> None:
    users = _collect_users_from_users_csv(
        [
            {
                "external_user_id": "309551566",
                "user_name": "Rkhbvs",
                "registration_time": "2024-01-01 09:00:00",
            }
        ]
    )
    supplemental = _collect_users_from_rows(
        [],
        [],
        [{"user_id": "309551566", "insert_time": "2024-01-02 10:00:00"}],
    )
    merged = _merge_user_records(users, supplemental)
    assert merged["309551566"].user_name == "Rkhbvs"


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


def test_parse_event_parameters_python_literal() -> None:
    params = _parse_event_parameters("[{'qv_number': 1}]")
    assert params == {"qv_number": 1}


def test_filter_legacy_csv_rows_by_username(tmp_path: Path) -> None:
    users_csv = tmp_path / "users.csv"
    main_csv = tmp_path / "main.csv"
    reviews_csv = tmp_path / "reviews.csv"
    events_csv = tmp_path / "events.csv"
    users_csv.write_text(
        "external_user_id,user_name,registration_time\n"
        "111,alice,2024-01-01 09:00:00\n"
        "222,bob,2024-01-02 09:00:00\n",
        encoding="utf-8",
    )
    main_csv.write_text(
        "user_id,user_name,qv_id,qv_number,qv_text,answer_text,insert_time\n"
        "111,alice,Q173,1,text,1. Да,2024-01-01 10:00:00\n"
        "222,bob,Q173,1,text,2. Нет,2024-01-02 10:00:00\n",
        encoding="utf-8",
    )
    reviews_csv.write_text(
        "user_id,user_name,qv_id,qv_number,qv_text,answer_text,insert_time\n",
        encoding="utf-8",
    )
    events_csv.write_text(
        "user_id,event_type,parameters,timestamp\n"
        '111,main_menu,{},2024-01-01 09:00:00\n'
        '222,main_menu,{},2024-01-02 09:00:00\n',
        encoding="utf-8",
    )

    users, main, reviews, events = filter_legacy_csv_rows(
        ["alice"],
        users_csv=users_csv,
        main_answers_csv=main_csv,
        reviews_csv=reviews_csv,
        events_csv=events_csv,
    )
    assert len(users) == 1
    assert users[0]["user_name"] == "alice"
    assert len(main) == 1
    assert main[0]["user_id"] == "111"
    assert len(events) == 1
    assert events[0]["user_id"] == "111"


def test_import_legacy_from_csv_by_usernames_dry_run(tmp_path: Path) -> None:
    users_csv = tmp_path / "users.csv"
    main_csv = tmp_path / "main.csv"
    reviews_csv = tmp_path / "reviews.csv"
    events_csv = tmp_path / "events.csv"
    users_csv.write_text(
        "external_user_id,user_name,registration_time\n"
        "333,Rkhbvs,2024-03-01 09:00:00\n",
        encoding="utf-8",
    )
    main_csv.write_text(
        "user_id,user_name,qv_id,qv_number,qv_text,answer_text,insert_time\n"
        "333,Rkhbvs,Q173,1,text,1. Да,2024-03-01 10:00:00\n",
        encoding="utf-8",
    )
    reviews_csv.write_text(
        "user_id,user_name,qv_id,qv_number,qv_text,answer_text,insert_time\n",
        encoding="utf-8",
    )
    events_csv.write_text(
        "user_id,event_type,parameters,timestamp\n"
        '333,main_menu,{},2024-03-01 09:00:00\n',
        encoding="utf-8",
    )
    stats = import_legacy_from_csv_by_usernames(
        {"schema": "wvs"},
        ["Rkhbvs"],
        users_csv=users_csv,
        main_answers_csv=main_csv,
        reviews_csv=reviews_csv,
        events_csv=events_csv,
        dry_run=True,
    )
    assert stats.users_created == 1
    assert stats.main_answers == 1
    assert stats.events_imported == 1


def test_import_legacy_dry_run(tmp_path: Path) -> None:
    users_csv = tmp_path / "users.csv"
    main_csv = tmp_path / "main.csv"
    reviews_csv = tmp_path / "reviews.csv"
    events_csv = tmp_path / "events.csv"
    users_csv.write_text(
        "external_user_id,user_name,registration_time\n"
        "111,alice,2024-01-01 09:00:00\n",
        encoding="utf-8",
    )
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
        users_csv=users_csv,
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
