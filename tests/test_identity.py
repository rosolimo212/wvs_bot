# coding: utf-8
"""Тесты стабильного user_id из channel + external_user_id."""

from __future__ import annotations

from core.identity import make_user_id, new_external_user_id


def test_make_user_id_stable() -> None:
    first = make_user_id("telegram", "12345")
    second = make_user_id("telegram", "12345")
    assert first == second
    assert first != make_user_id("console", "12345")


def test_new_external_user_id_is_uuid_like() -> None:
    value = new_external_user_id("streamlit")
    assert len(value) >= 32
