from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from datetime import datetime

from app.config import labels
from app.database.recording_db_operations import get_recording_by_link, get_recordings_by_tag
from app.database.tag_db_operations import get_tag_by_id
from app.keyboards import (
    choose_recordings_search_method_keyboard as recordings_keyboard,
    inline_active_tag_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import logger, user


class RecordingSearchStates(StatesGroup):
    waiting_for_meet_link = State()


@user.message(F.text == labels.GET_RECORD)
async def get_recording(message: Message):
    logger.info("get_recordings_call")
    await message.answer(
        text="Как вы хотите найти запись: по тегу или по ссылке?",
        reply_markup=recordings_keyboard,
    )


@user.callback_query(F.data == Callbacks.get_recording_by_tag_callback)
async def get_recording_by_tag(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите нужный тег:",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_search_mode_callback,
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
            on_archived_clicked_callback=None,
            on_item_create_clicked_callback=None,
        ),
    )


@user.callback_query(F.data.startswith(Callbacks.tag_clicked_in_search_mode_callback))
async def process_tag_selection(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return

    recordings = await get_recordings_by_tag(tag_id)
    if not recordings:
        await callback.message.edit_text(
            text=f"Записей с тегом '{tag.name}' не найдено.",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    else:
        response = f"Найденные записи с тегом '{tag.name}':\n\n"
        for recording in recordings:
            timestamp_str = datetime.fromtimestamp(recording.next_meeting_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            response += f"Ссылка: {recording.link}\nДата: {timestamp_str}\nID: {recording.id}\n\n"
        await callback.message.edit_text(
            text=response.strip(),
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await callback.answer("")


@user.callback_query(F.data == Callbacks.get_recording_by_link_callback)
async def start_recording_by_link(callback: CallbackQuery, state: FSMContext):
    await callback.answer("")
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
    )
    await state.set_state(RecordingSearchStates.waiting_for_meet_link)


@user.message(RecordingSearchStates.waiting_for_meet_link)
async def process_meet_link(message: Message, state: FSMContext):
    meet_link = message.text.strip()
    recording = await get_recording_by_link(meet_link)  # Здесь вызывается функция из recording_db_operations
    if recording:
        tag_name = recording.tag.name
        timestamp_str = datetime.fromtimestamp(recording.next_meeting_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        await message.answer(
            text=f"Найдена запись:\nСсылка: {recording.link}\nТег: {tag_name}\nДата: {timestamp_str}\nID: {recording.id}",
            reply_markup=main_actions_keyboard,
        )
    else:
        await message.answer(
            text=f"Запись с ссылкой '{meet_link}' не найдена!",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await state.clear()


@user.callback_query(F.data == Callbacks.cancel_primary_action_callback)
async def on_cancel_primary_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("")
    await callback.message.delete()
    await callback.message.answer(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой",
        reply_markup=main_actions_keyboard,
    )
    await state.clear()
