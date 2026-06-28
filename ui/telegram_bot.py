# coding: utf-8
"""
Telegram-клиент WVS на aiogram 3.

Цель:
    Полноценный клиент: тот же сценарий, что Streamlit, включая график страны.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, KeyboardButton, Message, ReplyKeyboardMarkup

from core.messages import (
    back_to_menu_button,
    button,
    change_name_button,
    confirm_name_button,
    message as dlg_message,
)
from core.models import (
    ACTION_NAME_CHANGE,
    ACTION_NAME_CONFIRMED,
    ACTION_NAME_ENTERED,
    Screen,
    UserIdentity,
)
from ui.base import build_app_service
from ui.find_country_delivery import deliver_find_country_telegram
from ui.helpers import apply_response, build_payload, store_identity
from ui.telegram_session import build_telegram_bot
from ui.interactive_client import (
    enrich_find_country_console,
    handle_name_entered,
    handle_raw_input,
    is_questionnaire_screen,
    questionnaire_actions,
    questionnaire_choice_buttons,
    return_later_from_questionnaire,
    submit_questionnaire_answer,
    sync_profile_from_db,
)


class Flow(StatesGroup):
    start = State()
    name_confirm = State()
    main_menu = State()
    learn_more = State()
    learn_more_answer = State()
    main_questionary = State()
    secondary_questionary = State()
    analytics = State()


def _make_keyboard(buttons: list[str]) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=label)] for label in buttons]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _identity_from_data(data: dict[str, Any]) -> UserIdentity:
    return UserIdentity(
        user_id=data["user_id"],
        internal_user_id=int(data["internal_user_id"]),
        external_user_id=data["external_user_id"],
    )


def _state_for_screen(screen: Screen) -> State:
    if screen == Screen.START:
        return Flow.start
    if screen == Screen.NAME_CONFIRM:
        return Flow.name_confirm
    if screen == Screen.LEARN_MORE:
        return Flow.learn_more
    if screen == Screen.LEARN_MORE_ANSWER:
        return Flow.learn_more_answer
    if screen == Screen.MAIN_QUESTIONARY:
        return Flow.main_questionary
    if screen == Screen.SECONDARY_QUESTIONARY:
        return Flow.secondary_questionary
    if screen in (Screen.FIND_COUNTRY, Screen.FIND_OWN_PLACE):
        return Flow.analytics
    return Flow.main_menu


async def _send_response(
    message: Message,
    state: FSMContext,
    *,
    bot: Bot,
    service,
    config: dict[str, Any],
    channel: str = "telegram",
) -> None:
    data = await state.get_data()
    identity = _identity_from_data(data)
    buttons = data.get("buttons", [])
    markup = _make_keyboard(buttons) if buttons else None

    delivery = deliver_find_country_telegram(service, identity, data, config, channel)
    await state.update_data(**data)

    if delivery is not None:
        await message.answer(delivery["text"], reply_markup=markup)
        if delivery.get("png_bytes"):
            await bot.send_photo(
                message.chat.id,
                BufferedInputFile(delivery["png_bytes"], filename="country_plot.png"),
            )
        return

    from ui.own_place_delivery import deliver_own_place_telegram

    own_place_delivery = deliver_own_place_telegram(data, channel)
    await state.update_data(**data)

    if own_place_delivery is not None:
        await message.answer(own_place_delivery["text"], reply_markup=markup)
        for png_bytes, filename in own_place_delivery.get("png_list", []):
            await bot.send_photo(
                message.chat.id,
                BufferedInputFile(png_bytes, filename=filename),
            )
        return

    text = data.get("last_text", "")
    await message.answer(text, reply_markup=markup)


async def run_telegram(config: dict[str, Any]) -> None:
    service = build_app_service(config)
    channel = "telegram"

    bot = build_telegram_bot(config)
    dp = Dispatcher(storage=MemoryStorage())

    async def _reply(message: Message, state: FSMContext) -> None:
        await _send_response(
            message,
            state,
            bot=bot,
            service=service,
            config=config,
            channel=channel,
        )

    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        external_user_id = str(message.from_user.id)
        identity = service.logger.ensure_user(channel, external_user_id)
        context = {"telegram_username": message.from_user.username or ""}
        response = service.handle_start(identity, channel, context)

        session_state: dict[str, Any] = {}
        store_identity(session_state, identity)
        sync_profile_from_db(service, identity, session_state)
        apply_response(session_state, response)
        session_state["main_questionary_complete"] = service.is_main_questionary_complete(identity)
        await state.update_data(**session_state)
        await state.set_state(_state_for_screen(response.screen))
        await _reply(message, state)

    @dp.message(Flow.start)
    async def on_start_screen(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        user_name = (message.text or "").strip()
        handle_name_entered(service, identity, channel, data, user_name)
        await state.update_data(**data)
        await state.set_state(_state_for_screen(Screen(data["screen"])))
        await _reply(message, state)

    @dp.message(Flow.name_confirm)
    async def on_name_confirm(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        text = (message.text or "").strip()
        payload = build_payload(
            user_name=data.get("user_name"),
            registration_date=data.get("registration_date"),
            text=text,
            screen=Screen.NAME_CONFIRM,
        )

        if text == confirm_name_button(channel):
            action = ACTION_NAME_CONFIRMED
        elif text == change_name_button(channel):
            action = ACTION_NAME_CHANGE
        else:
            action = ACTION_NAME_ENTERED
            payload = build_payload(text=text)

        response = service.handle_action(identity, channel, action, payload)
        reg_name = None
        reg_date = None
        if response.screen == Screen.MAIN_MENU:
            sync_profile_from_db(service, identity, data)
            reg_name = data.get("user_name")
            reg_date = data.get("registration_date")

        apply_response(data, response, user_name=reg_name, registration_date=reg_date)
        data["main_questionary_complete"] = service.is_main_questionary_complete(identity)
        await state.update_data(**data)
        await state.set_state(_state_for_screen(response.screen))
        await _reply(message, state)

    @dp.message(Flow.main_questionary, F.text)
    async def on_main_questionary(message: Message, state: FSMContext) -> None:
        await _on_questionnaire(message, state, Screen.MAIN_QUESTIONARY.value)

    @dp.message(Flow.secondary_questionary, F.text)
    async def on_secondary_questionary(message: Message, state: FSMContext) -> None:
        await _on_questionnaire(message, state, Screen.SECONDARY_QUESTIONARY.value)

    async def _on_questionnaire(message: Message, state: FSMContext, screen: str) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        text = (message.text or "").strip()
        return_later_label = data.get("meta", {}).get("return_later_label", button("return_later", channel))
        answer_action, return_action = questionnaire_actions(screen)

        if text == return_later_label:
            return_later_from_questionnaire(
                service,
                identity,
                channel,
                data,
                screen=screen,
                return_action=return_action,
            )
        else:
            choices = questionnaire_choice_buttons(data, channel)
            input_mode = data.get("meta", {}).get("input_mode", "choice")
            if input_mode == "text" and text not in choices:
                selected = ""
                answer = text
            elif text in choices:
                selected = text
                answer = text
            else:
                await message.answer(dlg_message("main_answer_invalid", channel))
                return

            submit_questionnaire_answer(
                service,
                identity,
                channel,
                data,
                screen=screen,
                answer_action=answer_action,
                answer=answer,
                selected=selected,
            )

        await state.update_data(**data)
        await state.set_state(_state_for_screen(Screen(data["screen"])))
        await _reply(message, state)

    @dp.message(Flow.main_menu, F.text)
    async def on_main_menu(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        text = message.text or ""
        handle_raw_input(service, identity, channel, data, text, config=config)
        await state.update_data(**data)
        await state.set_state(_state_for_screen(Screen(data["screen"])))
        await _reply(message, state)

    @dp.message(Flow.learn_more, F.text)
    async def on_learn_more(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        text = message.text or ""
        handle_raw_input(service, identity, channel, data, text, config=config)
        await state.update_data(**data)
        await state.set_state(_state_for_screen(Screen(data["screen"])))
        await _reply(message, state)

    @dp.message(Flow.learn_more_answer, F.text)
    async def on_learn_more_answer(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        text = message.text or ""
        handle_raw_input(service, identity, channel, data, text, config=config)
        await state.update_data(**data)
        await state.set_state(_state_for_screen(Screen(data["screen"])))
        await _reply(message, state)

    @dp.message(Flow.analytics, F.text)
    async def on_analytics(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        identity = _identity_from_data(data)
        text = message.text or ""
        handle_raw_input(service, identity, channel, data, text, config=config)
        await state.update_data(**data)
        await state.set_state(_state_for_screen(Screen(data["screen"])))
        await _reply(message, state)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
