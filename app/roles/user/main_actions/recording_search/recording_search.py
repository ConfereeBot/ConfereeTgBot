from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from app.config import labels
from app.database.conference_db_operations import get_conferences_by_tag, get_conference_by_link
from app.database.recording_db_operations import get_recording_by_id
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
    """Handle the command to search for recordings."""
    logger.info("get_recordings_call")
    await message.answer(
        text="Как вы хотите найти запись: по тегу или по ссылке?",
        reply_markup=recordings_keyboard,
    )


@user.callback_query(F.data == Callbacks.get_recording_by_tag_callback)
async def get_recording_by_tag(callback: CallbackQuery):
    """Start the process of searching recordings by tag."""
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
    """Process the selection of a tag for searching conferences."""
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return

    conferences = await get_conferences_by_tag(tag_id)
    if not conferences:
        await callback.message.edit_text(
            text=f"Конференций с тегом '{tag.name}' не найдено.",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    else:
        response = f"Найденные конференции с тегом '{tag.name}':\n\n"
        buttons = []
        for i, conference in enumerate(conferences, 1):  # Нумерация начинается с 1
            timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            response += f"{i}. Конференция: {conference.link}\nДата: {timestamp_str}\n"
            if conference.recordings:
                response += "Записи:\n"
                for recording_id in conference.recordings:
                    recording = await get_recording_by_id(str(recording_id))
                    if recording:
                        response += f"  - {recording.link}\n"
                    else:
                        response += f"  - Запись не найдена\n"
            else:
                response += "Записей нет.\n"
            response += "\n"
            # Delete www and protocol from link
            clean_link = conference.link.replace("https://", "").replace("http://", "").replace("www.", "")
            # Date and time format
            short_date = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M')
            # Button text: NUM. LINK, DATE_TIME
            button_text = f"{i}. {clean_link}, {short_date}"
            buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"open_conference:{conference.id}"
                )
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="Отменить", callback_data=Callbacks.cancel_primary_action_callback)]
        )

        await callback.message.edit_text(
            text=response.strip(),
            reply_markup=keyboard,
        )
    await callback.answer("")


@user.callback_query(F.data == Callbacks.get_recording_by_link_callback)
async def start_recording_by_link(callback: CallbackQuery, state: FSMContext):
    """Start the process of searching recordings by conference link."""
    await callback.answer("")
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
    )
    await state.set_state(RecordingSearchStates.waiting_for_meet_link)


@user.message(RecordingSearchStates.waiting_for_meet_link)
async def process_meet_link(message: Message, state: FSMContext):
    """Process the entered Google Meet link to find the conference and its recordings."""
    meet_link = message.text.strip()
    conference = await get_conference_by_link(meet_link)
    if conference:
        tag = await get_tag_by_id(str(conference.tag_id))  # Fetch tag by tag_id
        tag_name = tag.name if tag else "Неизвестный тег"
        timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        response = f"Найдена конференция:\nСсылка: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}\n"
        if conference.recordings:
            response += "Записи:\n"
            buttons = []
            for recording_id in conference.recordings:
                recording = await get_recording_by_id(str(recording_id))
                if recording:
                    response += f"  - {recording.link}\n"
                    buttons.append(
                        InlineKeyboardButton(
                            text=f"Открыть запись: {recording.link.split('/')[-1]}",
                            callback_data=f"open_recording:{recording.id}"
                        )
                    )
                else:
                    response += f"  - Запись не найдена\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
        else:
            response += "Записей нет."
            keyboard = main_actions_keyboard
        await message.answer(
            text=response.strip(),
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            text=f"Конференция с ссылкой '{meet_link}' не найдена!",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await state.clear()


@user.callback_query(F.data == Callbacks.cancel_primary_action_callback)
async def on_cancel_primary_callback(callback: CallbackQuery, state: FSMContext):
    """Handle the cancellation of the current action."""
    await callback.answer("")
    await callback.message.delete()
    await callback.message.answer(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой.",
        reply_markup=main_actions_keyboard,
    )
    await state.clear()


@user.callback_query(F.data.startswith("open_recording"))
async def handle_recording_button(callback: CallbackQuery):
    """Handle the click on a recording button (stub for now)."""
    recording_id = callback.data.split(":")[1]
    await callback.answer(f"Заглушка: открытие записи с ID {recording_id} пока не реализовано!", show_alert=True)


@user.callback_query(F.data.startswith("open_conference"))
async def handle_conference_button(callback: CallbackQuery):
    """Handle the click on a conference button (stub for now)."""
    conference_id = callback.data.split(":")[1]
    await callback.answer(f"Заглушка: открытие конференции с ID {conference_id} пока не реализовано!", show_alert=True)
