# coding: utf-8
"""Оркестрация исходящих коммуникаций (dry-run / send)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aiogram.enums import ParseMode

from core.communication.messages import load_template, render_template_text
from core.communication.segments import (
    CommunicationRecipient,
    resolve_segment_recipients,
)
from core.communication.store import (
    STATUS_FAILED,
    STATUS_SENT,
    allocate_communication_id,
    has_template_attempt,
    insert_communication,
    is_rate_limited,
)
from core.communication.telegram_delivery import send_telegram_text
from ui.telegram_format import markdown_bold_to_telegram_html
from ui.telegram_session import build_telegram_bot

DEFAULT_PAUSE_SEC = 2.0


@dataclass
class RecipientPlan:
    recipient: CommunicationRecipient
    text: str
    skip_reason: str | None = None


@dataclass
class CommunicationRunResult:
    template_id: str
    segment: str
    planned: list[RecipientPlan] = field(default_factory=list)
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    dry_run: bool = False


def _format_outbound_text(text: str) -> str:
    return markdown_bold_to_telegram_html(text)


def _status_failed(exc: BaseException) -> str:
    name = type(exc).__name__
    detail = str(exc).replace("\n", " ").strip()
    if len(detail) > 180:
        detail = detail[:177] + "..."
    return f"{STATUS_FAILED}:{name}:{detail}" if detail else f"{STATUS_FAILED}:{name}"


def prepare_communication_plans(
    config: dict[str, Any],
    *,
    template_id: str,
    segment: str,
    messages_path: Path | None = None,
    now: datetime | None = None,
    check_store: bool = True,
) -> list[RecipientPlan]:
    template = load_template(template_id, path=messages_path)
    recipients = resolve_segment_recipients(config, segment)
    moment = now or datetime.now()
    logging_config = config["logging"]
    plans: list[RecipientPlan] = []

    for recipient in recipients:
        text = render_template_text(
            template,
            channel=recipient.registration_channel,
            user_name=recipient.user_name,
        )
        skip_reason: str | None = None
        if check_store:
            if has_template_attempt(
                logging_config,
                user_id=recipient.user_id,
                template_id=template.template_id,
            ):
                skip_reason = "already_attempted"
            elif is_rate_limited(
                logging_config,
                user_id=recipient.user_id,
                now=moment,
            ):
                skip_reason = "rate_limited"
        plans.append(
            RecipientPlan(recipient=recipient, text=text, skip_reason=skip_reason)
        )
    return plans


async def run_communication(
    config: dict[str, Any],
    *,
    template_id: str,
    segment: str,
    dry_run: bool = False,
    messages_path: Path | None = None,
    pause_sec: float = DEFAULT_PAUSE_SEC,
    now: datetime | None = None,
) -> CommunicationRunResult:
    """
    Готовит рассылку и при dry_run=False отправляет в Telegram.

    На каждую реальную попытку (успех/ошибка API) — INSERT в wvs.communications
    с заранее выделенным communication_id.
    """
    template = load_template(template_id, path=messages_path)
    plans = prepare_communication_plans(
        config,
        template_id=template.template_id,
        segment=segment,
        messages_path=messages_path,
        now=now,
        check_store=True,
    )
    result = CommunicationRunResult(
        template_id=template.template_id,
        segment=segment,
        planned=plans,
        dry_run=dry_run,
    )

    if dry_run:
        result.skipped = sum(1 for plan in plans if plan.skip_reason)
        return result

    logging_config = config["logging"]
    bot = build_telegram_bot(config)
    try:
        first_send = True
        for plan in plans:
            if plan.skip_reason:
                result.skipped += 1
                continue
            if not first_send and pause_sec > 0:
                await asyncio.sleep(pause_sec)
            first_send = False

            communication_id = allocate_communication_id(logging_config)
            sending_time = datetime.now()
            html_text = _format_outbound_text(plan.text)
            try:
                await send_telegram_text(
                    config,
                    chat_id=plan.recipient.external_user_id,
                    text=html_text,
                    parse_mode=ParseMode.HTML,
                    bot=bot,
                )
                status = STATUS_SENT
                result.sent += 1
            except Exception as exc:
                status = _status_failed(exc)
                result.failed += 1

            insert_communication(
                logging_config,
                communication_id=communication_id,
                user_id=plan.recipient.user_id,
                template_id=template.template_id,
                sending_time=sending_time,
                status=status,
            )
    finally:
        await bot.session.close()

    return result


def format_run_summary(result: CommunicationRunResult, *, preview_limit: int = 5) -> str:
    lines = [
        f"template={result.template_id}",
        f"segment={result.segment}",
        f"recipients={len(result.planned)}",
        f"dry_run={result.dry_run}",
        f"sent={result.sent} failed={result.failed} skipped={result.skipped}",
        "",
        "preview:",
    ]
    for plan in result.planned[:preview_limit]:
        skip = f" skip={plan.skip_reason}" if plan.skip_reason else ""
        lines.append(
            f"- {plan.recipient.user_id} / {plan.recipient.external_user_id} "
            f"({plan.recipient.user_name}){skip}"
        )
        preview = plan.text.replace("\n", "\\n")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        lines.append(f"  text: {preview}")
    if len(result.planned) > preview_limit:
        lines.append(f"... и ещё {len(result.planned) - preview_limit}")
    return "\n".join(lines)
