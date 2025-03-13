from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import labels
from app.database.conference_db_operations import add_conference_to_db
from app.database.tag_db_operations import get_tag_by_id
from app.keyboards import (
    inline_active_tag_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import logger, user


class RecordingCreateStates(StatesGroup):
    waiting_for_tag = State()
    waiting_for_meet_link = State()


@user.message(F.text == labels.RECORD)
async def start_recording(message: Message):
    logger.info("start_recording_call")
    await message.answer(
        text="Выберите тег для новой конференции:",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_recording_mode_callback,
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
            on_archived_clicked_callback=None,
            on_item_create_clicked_callback=None,
        ),
    )


@user.callback_query(F.data.startswith(Callbacks.tag_clicked_in_recording_mode_callback))
async def process_tag_for_recording(callback: CallbackQuery, state: FSMContext):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return

    await state.update_data(tag=tag)
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
    )
    await state.set_state(RecordingCreateStates.waiting_for_meet_link)
    await callback.answer("")


@user.message(RecordingCreateStates.waiting_for_meet_link)
async def process_meet_link_for_recording(message: Message, state: FSMContext):
    meet_link = message.text.strip()
    state_data = await state.get_data()
    tag = state_data.get("tag")

    if not tag:
        await message.answer(
            text="Ошибка: тег не выбран! Попробуйте начать заново.",
            reply_markup=main_actions_keyboard,
        )
        await state.clear()
        return

    success, response, conference_id = await add_conference_to_db(meet_link, tag)
    if success:
        await message.answer(
            text=f"{response}\nID конференции: {conference_id}\nЗаписей пока нет.",
            reply_markup=main_actions_keyboard,
        )
    else:
        await message.answer(
            text=response,
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await state.clear()
