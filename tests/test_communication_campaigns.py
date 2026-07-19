from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.communication.campaigns import prepare_communication_plans, run_communication
from core.communication.messages import (
    clear_messages_cache,
    load_template,
    render_template_text,
)
from core.communication.segments import (
    SEGMENT_TEST,
    TEST_USER_ID,
    resolve_segment_recipients,
)
from core.communication.store import STATUS_FAILED, STATUS_SENT


@pytest.fixture(autouse=True)
def _clear_template_cache() -> None:
    clear_messages_cache()
    yield
    clear_messages_cache()


def test_load_stub_template() -> None:
    template = load_template("stub_empty")
    assert template.template_id == "stub_empty"
    text = render_template_text(template, channel="telegram", user_name="Roman")
    assert "Roman" in text
    assert "{user_name}" not in text


def test_resolve_test_segment_uses_stats_chat() -> None:
    config = {
        "logging": {"schema": "wvs"},
        "communication": {"daily_audience_report": {"chat_id": "-10042"}},
    }
    recipients = resolve_segment_recipients(config, SEGMENT_TEST)
    assert len(recipients) == 1
    assert recipients[0].user_id == TEST_USER_ID
    assert recipients[0].external_user_id == "-10042"
    assert recipients[0].user_name == "team"


def test_prepare_plans_marks_skips() -> None:
    config = {
        "logging": {"schema": "wvs"},
        "communication": {"daily_audience_report": {"chat_id": "-10042"}},
    }
    with patch(
        "core.communication.campaigns.has_template_attempt",
        return_value=True,
    ):
        with patch("core.communication.campaigns.is_rate_limited", return_value=False):
            plans = prepare_communication_plans(
                config,
                template_id="stub_empty",
                segment="test",
            )
    assert len(plans) == 1
    assert plans[0].skip_reason == "already_attempted"


@pytest.mark.asyncio
async def test_run_communication_dry_run_no_send() -> None:
    config = {
        "logging": {"schema": "wvs"},
        "communication": {"daily_audience_report": {"chat_id": "-10042"}},
        "telegram": {"token": "x"},
    }
    with patch("core.communication.campaigns.has_template_attempt", return_value=False):
        with patch("core.communication.campaigns.is_rate_limited", return_value=False):
            with patch(
                "core.communication.campaigns.send_telegram_text",
                new_callable=AsyncMock,
            ) as send:
                result = await run_communication(
                    config,
                    template_id="stub_empty",
                    segment="test",
                    dry_run=True,
                )
    assert result.dry_run is True
    assert result.sent == 0
    assert len(result.planned) == 1
    send.assert_not_called()


@pytest.mark.asyncio
async def test_run_communication_inserts_sent_and_failed() -> None:
    config = {
        "logging": {"schema": "wvs"},
        "communication": {"daily_audience_report": {"chat_id": "-10042"}},
        "telegram": {"token": "x"},
    }
    inserts: list[dict] = []

    async def fake_send(*args, **kwargs):
        raise RuntimeError("blocked")

    with patch("core.communication.campaigns.has_template_attempt", return_value=False):
        with patch("core.communication.campaigns.is_rate_limited", return_value=False):
            with patch(
                "core.communication.campaigns.allocate_communication_id",
                return_value=7,
            ):
                with patch(
                    "core.communication.campaigns.insert_communication",
                    side_effect=lambda _cfg, **kwargs: inserts.append(kwargs),
                ):
                    with patch(
                        "core.communication.campaigns.build_telegram_bot",
                    ) as build_bot:
                        build_bot.return_value.session.close = AsyncMock()
                        with patch(
                            "core.communication.campaigns.send_telegram_text",
                            side_effect=fake_send,
                        ):
                            result = await run_communication(
                                config,
                                template_id="stub_empty",
                                segment="test",
                                dry_run=False,
                                pause_sec=0,
                            )

    assert result.failed == 1
    assert result.sent == 0
    assert len(inserts) == 1
    assert inserts[0]["communication_id"] == 7
    assert inserts[0]["user_id"] == TEST_USER_ID
    assert inserts[0]["template_id"] == "stub_empty"
    assert inserts[0]["status"].startswith(STATUS_FAILED)
    assert STATUS_SENT not in inserts[0]["status"]


def test_custom_messages_file(tmp_path: Path) -> None:
    path = tmp_path / "msgs.json"
    path.write_text(
        """
        {
          "templates": {
            "hello": {
              "template_id": "hello",
              "when": "test",
              "default": "Hi, {user_name}",
              "telegram": "TG hi, {user_name}"
            }
          }
        }
        """,
        encoding="utf-8",
    )
    clear_messages_cache()
    template = load_template("hello", path=path)
    assert (
        render_template_text(template, channel="telegram", user_name="Ann")
        == "TG hi, Ann"
    )
