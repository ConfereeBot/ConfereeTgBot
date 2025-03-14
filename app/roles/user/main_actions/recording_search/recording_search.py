from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from app.config import labels
from app.database.conference_db_operations import get_conferences_by_tag, get_conference_by_link, get_conference_by_id
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
    browsing_conference = State()


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
async def process_tag_selection(callback: CallbackQuery, state: FSMContext):
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
        for i, conference in enumerate(conferences, 1):
            timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            response += f"{i}. Конференция: {conference.link}\nДата: {timestamp_str}\n\n"
            clean_link = conference.link.replace("https://", "").replace("http://", "").replace("www.", "")
            short_date = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M')
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
        await state.update_data(tag_id=tag_id)
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
        tag = await get_tag_by_id(str(conference.tag_id))
        tag_name = tag.name if tag else "Неизвестный тег"
        timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        response = f"Найдена конференция:\nСсылка: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}"
        buttons = []
        if conference.recordings:
            for recording_id in conference.recordings:
                recording = await get_recording_by_id(str(recording_id))
                if recording:
                    recording_date = datetime.fromtimestamp(recording.timestamp).strftime('%Y-%m-%d %H:%M')
                    buttons.append(
                        InlineKeyboardButton(
                            text=f"Открыть запись {recording_date}",
                            url=recording.link
                        )
                    )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[btn] for btn in buttons]) if buttons else InlineKeyboardMarkup(inline_keyboard=[])
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="Отменить", callback_data=Callbacks.cancel_primary_action_callback)]
        )
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


@user.callback_query(F.data.startswith("open_conference"))
async def handle_conference_button(callback: CallbackQuery, state: FSMContext):
    """Handle the click on a conference button to show its recordings."""
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    tag = await get_tag_by_id(str(conference.tag_id))
    tag_name = tag.name if tag else "Неизвестный тег"
    timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    response = f"Конференция: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}"
    buttons = []
    if conference.recordings:
        for recording_id in conference.recordings:
            recording = await get_recording_by_id(str(recording_id))
            if recording:
                recording_date = datetime.fromtimestamp(recording.timestamp).strftime('%Y-%m-%d %H:%M')
                buttons.append(
                    InlineKeyboardButton(
                        text=f"Открыть запись {recording_date}",
                        url=recording.link
                    )
                )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons]) if buttons else InlineKeyboardMarkup(
        inline_keyboard=[])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="Назад", callback_data=f"{Callbacks.back_to_tag_in_search_mode}:{conference.tag_id}")]
    )

    await callback.message.edit_text(
        text=response.strip(),
        reply_markup=keyboard,
    )
    await state.set_state(RecordingSearchStates.browsing_conference)
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.back_to_tag_in_search_mode))
async def handle_back_to_tag_in_search_mode(callback: CallbackQuery, state: FSMContext):
    """Handle the 'Back' button to return to the list of conferences by tag."""
    tag_id = callback.data.split(":")[1]
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден!", show_alert=True)
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
        for i, conference in enumerate(conferences, 1):
            timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            response += f"{i}. Конференция: {conference.link}\nДата: {timestamp_str}\n\n"
            clean_link = conference.link.replace("https://", "").replace("http://", "").replace("www.", "")
            short_date = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M')
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
    await state.clear()
    await callback.answer("")
