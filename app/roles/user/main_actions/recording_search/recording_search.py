from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from app.config import labels
from app.config.roles import Role
from app.database.conference_db_operations import (
    get_conferences_by_tag,
    get_conference_by_link,
    get_conference_by_id,
)
from app.database.recording_db_operations import get_recording_by_id
from app.database.tag_db_operations import get_tag_by_id
from app.database.user_db_operations import get_user_by_telegram_tag
from app.keyboards import (
    choose_recordings_search_method_keyboard as recordings_keyboard,
    inline_active_tag_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.admin.admin import admin  # Импортируем admin для удаления
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user
from app.utils.logger import logger


class RecordingSearchStates(StatesGroup):
    waiting_for_meet_link = State()
    browsing_conference = State()
    confirming_conference_deletion = State()


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
async def process_tag_selection(callback: CallbackQuery, state: FSMContext):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
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
    await callback.answer("")
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
    )
    await state.set_state(RecordingSearchStates.waiting_for_meet_link)


@user.message(RecordingSearchStates.waiting_for_meet_link)
async def process_meet_link(message: Message, state: FSMContext):
    meet_link = message.text.strip()
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    conference = await get_conference_by_link(meet_link)
    if conference:
        tag = await get_tag_by_id(str(conference.tag_id))
        tag_name = tag.name if tag else "Неизвестный тег"
        timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        if conference.recordings:
            response = f"Найдена конференция:\nСсылка: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}"
        else:
            response = f"Найдена конференция:\nСсылка: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}\n\nЗаписей пока нет."
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
        if user.role >= Role.ADMIN:
            keyboard.inline_keyboard.extend([
                [InlineKeyboardButton(text="🗑️ Удалить",
                                      callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
            ])
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="↩ Назад", callback_data=Callbacks.cancel_primary_action_callback)]
        )
        await message.answer(
            text=response.strip(),
            reply_markup=keyboard,
        )
        await state.set_state(RecordingSearchStates.browsing_conference)
    else:
        await message.answer(
            text=f"Конференция с ссылкой '{meet_link}' не найдена!",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await state.clear()


@user.callback_query(F.data == Callbacks.cancel_primary_action_callback)
async def on_cancel_primary_callback(callback: CallbackQuery, state: FSMContext):
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    await callback.answer("")
    await callback.message.delete()
    await callback.message.answer(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой.",
        reply_markup=main_actions_keyboard(user.role),
    )
    await state.clear()


@user.callback_query(F.data.startswith("open_conference"))
async def handle_conference_button(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    tag = await get_tag_by_id(str(conference.tag_id))
    tag_name = tag.name if tag else "Неизвестный тег"
    timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    if conference.recordings:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}"
    else:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}\n\nЗаписей пока нет."
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
    if user.role >= Role.ADMIN:
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="🗑️ Удалить",
                                  callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
        ])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="↩ Назад",
                              callback_data=f"{Callbacks.back_to_tag_in_search_mode}:{conference.tag_id}")]
    )

    await callback.message.edit_text(
        text=response.strip(),
        reply_markup=keyboard,
    )
    await state.set_state(RecordingSearchStates.browsing_conference)
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.back_to_tag_in_search_mode))
async def handle_back_to_tag_in_search_mode(callback: CallbackQuery, state: FSMContext):
    tag_id = callback.data.split(":")[1]
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
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


@admin.callback_query(F.data.startswith(Callbacks.delete_conference_callback))
async def handle_delete_conference(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    await state.update_data(conference_id=conference_id)
    await callback.message.edit_text(
        text=f"Вы уверены, что хотите удалить конференцию и все связанные с ней записи?\nСсылка: {conference.link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить",
                                  callback_data=f"{Callbacks.confirm_delete_conference}:{conference_id}"),
             InlineKeyboardButton(text="Отменить",
                                  callback_data=f"{Callbacks.cancel_delete_conference}:{conference_id}")],
        ]),
    )
    await state.set_state(RecordingSearchStates.confirming_conference_deletion)
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.confirm_delete_conference))
async def confirm_delete_conference(callback: CallbackQuery, state: FSMContext):
    from app.database.conference_db_operations import delete_conference_by_id  # Импорт внутри функции
    conference_id = callback.data.split(":")[1]
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    success, response = await delete_conference_by_id(conference_id)
    if success:
        await callback.message.delete()
        await callback.message.answer(
            text=response,
            reply_markup=main_actions_keyboard(user.role),
        )
    else:
        await callback.message.answer(
            text=response,
            reply_markup=main_actions_keyboard(user.role),
        )
    await state.clear()
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.cancel_delete_conference))
async def cancel_delete_conference(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        await state.clear()
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    tag = await get_tag_by_id(str(conference.tag_id))
    tag_name = tag.name if tag else "Неизвестный тег"
    timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    if conference.recordings:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}"
    else:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nДата: {timestamp_str}\n\nЗаписей пока нет."
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
    if user.role >= Role.ADMIN:
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="🗑️ Удалить",
                                  callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
        ])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="↩ Назад",
                              callback_data=f"{Callbacks.back_to_tag_in_search_mode}:{conference.tag_id}")]
    )

    await callback.message.edit_text(
        text=response.strip(),
        reply_markup=keyboard,
    )
    await state.set_state(RecordingSearchStates.browsing_conference)
    await callback.answer("")
