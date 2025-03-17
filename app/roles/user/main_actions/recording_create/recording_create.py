from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from bson import ObjectId

from app.config import labels
from app.database.conference_db_operations import add_conference_to_db, conference_exists_by_link
from app.database.tag_db_operations import get_tag_by_id
from app.database.user_db_operations import get_user_by_telegram_tag
from app.keyboards import (
    inline_active_tag_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.admin.admin import admin  # Импортируем роутер admin
from app.roles.user.callbacks_enum import Callbacks
from app.utils.logger import logger


class RecordingCreateStates(StatesGroup):
    waiting_for_tag = State()
    waiting_for_meet_link = State()
    waiting_for_timezone = State()
    waiting_for_start_date = State()
    waiting_for_recurrence = State()
    waiting_for_periodicity = State()


@admin.message(F.text == labels.RECORD)
async def start_recording(message: Message, state: FSMContext):
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
    await state.set_state(RecordingCreateStates.waiting_for_tag)


@admin.callback_query(F.data.startswith(Callbacks.tag_clicked_in_recording_mode_callback))
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

    print(f"Got tag {tag} in tag processing for conf adding. Found by id {tag_id}")
    await state.update_data(tag_id=tag_id)
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=Callbacks.back_to_tag_in_create_conference_mode)]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_meet_link)
    await callback.answer("")


@admin.callback_query(F.data == Callbacks.back_to_tag_in_create_conference_mode,
                      RecordingCreateStates.waiting_for_meet_link)
async def back_to_tag_from_link(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Выберите тег для новой конференции:",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_recording_mode_callback,
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
            on_archived_clicked_callback=None,
            on_item_create_clicked_callback=None,
        ),
    )
    await state.set_state(RecordingCreateStates.waiting_for_tag)
    await callback.answer("")


@admin.message(RecordingCreateStates.waiting_for_meet_link)
async def process_meet_link_for_recording(message: Message, state: FSMContext):
    meet_link = message.text.strip()
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    if not tag_id:
        await message.answer(
            text="Ошибка: тег не выбран! Попробуйте начать заново.",
            reply_markup=main_actions_keyboard(user.role),
        )
        await state.clear()
        return

    if not meet_link.startswith("https://meet.google.com/") or len(meet_link.split("/")[-1]) < 8:
        await message.answer(
            text="Ссылка некорректная, поддерживаются только ссылки Google Meet (https://meet.google.com/). Попробуйте снова:",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
        return

    if await conference_exists_by_link(meet_link):
        await message.answer(
            text=f"Конференция с ссылкой '{meet_link}' уже существует! Проверьте корректность ссылки и попробуйте снова:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data=Callbacks.back_to_tag_in_create_conference_mode)]
            ]),
        )
        return

    await state.update_data(meet_link=meet_link)
    await message.answer(
        text="Укажите тайм-зону относительно UTC (например, +3 или -5):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_link")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_timezone)


@admin.callback_query(F.data == "back_to_link", RecordingCreateStates.waiting_for_timezone)
async def back_to_link_from_timezone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=Callbacks.back_to_tag_in_create_conference_mode)]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_meet_link)
    await callback.answer("")


@admin.message(RecordingCreateStates.waiting_for_timezone)
async def process_timezone(message: Message, state: FSMContext):
    timezone_str = message.text.strip()
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    try:
        timezone = int(timezone_str)
        if not -12 <= timezone <= 14:
            raise ValueError
    except ValueError:
        await message.answer(
            text="Ошибка: неверный формат тайм-зоны! Введите число от -12 до +14 (например, +3 или -5). Повторите ввод:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_to_link")]
            ]),
        )
        return

    await state.update_data(timezone=timezone)
    await message.answer(
        text="Введите дату начала конференции в формате 'ДЕНЬ.МЕСЯЦ.ГОД ЧАСЫ:МИНУТЫ:СЕКУНДЫ' (например, 15.03.2025 14:30:00):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_timezone")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_start_date)


@admin.callback_query(F.data == "back_to_timezone", RecordingCreateStates.waiting_for_start_date)
async def back_to_timezone_from_date(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Укажите тайм-зону относительно UTC (например, +3 или -5):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_link")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_timezone)
    await callback.answer("")


@admin.message(RecordingCreateStates.waiting_for_start_date)
async def process_start_date(message: Message, state: FSMContext):
    start_date_str = message.text.strip()
    state_data = await state.get_data()
    timezone = state_data.get("timezone")
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    try:
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y %H:%M:%S")
        timestamp = int(start_date.timestamp()) - (timezone * 3600)
        current_time = int(datetime.now().timestamp())

        if timestamp < current_time:
            await message.answer(
                text="Ошибка: указанная дата и время находятся в прошлом! Введите будущую дату:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_timezone")]
                ]),
            )
            return

    except ValueError:
        await message.answer(
            text="Ошибка: неверный формат даты! Используйте 'ДЕНЬ.МЕСЯЦ.ГОД ЧАСЫ:МИНУТЫ:СЕКУНДЫ' (например, 15.03.2025 14:30:00). Повторите ввод:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_to_timezone")]
            ]),
        )
        return

    await state.update_data(timestamp=timestamp)
    await message.answer(
        text="Это регулярная встреча?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="recurrence_yes"),
             InlineKeyboardButton(text="Нет", callback_data="recurrence_no")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_timezone")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_recurrence)


@admin.callback_query(F.data == "back_to_timezone", RecordingCreateStates.waiting_for_recurrence)
async def back_to_timezone_from_recurrence(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Укажите тайм-зону относительно UTC (например, +3 или -5):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_link")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_timezone)
    await callback.answer("")


@admin.callback_query(F.data.startswith("recurrence_"), RecordingCreateStates.waiting_for_recurrence)
async def process_recurrence(callback: CallbackQuery, state: FSMContext):
    recurrence = callback.data == "recurrence_yes"
    await state.update_data(recurrence=recurrence)

    if recurrence:
        await callback.message.edit_text(
            text="С какой периодичностью повторяется встреча?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1 неделя", callback_data="period_1"),
                 InlineKeyboardButton(text="2 недели", callback_data="period_2")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_date")]
            ]),
        )
        await state.set_state(RecordingCreateStates.waiting_for_periodicity)
    else:
        await finish_recording(callback, state)
    await callback.answer("")


@admin.callback_query(F.data == "back_to_date", RecordingCreateStates.waiting_for_periodicity)
async def back_to_date_from_periodicity(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Это регулярная встреча?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="recurrence_yes"),
             InlineKeyboardButton(text="Нет", callback_data="recurrence_no")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_timezone")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_recurrence)
    await callback.answer("")


@admin.callback_query(F.data.startswith("period_"), RecordingCreateStates.waiting_for_periodicity)
async def process_periodicity(callback: CallbackQuery, state: FSMContext):
    periodicity = int(callback.data.split("_")[1])
    await state.update_data(periodicity=periodicity)
    await finish_recording(callback, state)
    await callback.answer("")


async def finish_recording(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    meet_link = state_data.get("meet_link")
    timestamp = state_data.get("timestamp")
    timezone = state_data.get("timezone")
    recurrence = state_data.get("recurrence")
    periodicity = state_data.get("periodicity", None)
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    print("Add conf with values", tag_id, meet_link, timestamp, timezone, recurrence, periodicity)

    success, response = await add_conference_to_db(
        meet_link=meet_link,
        tag_id=ObjectId(tag_id),
        timestamp=timestamp,
        timezone=timezone,
        periodicity=periodicity if recurrence else None
    )

    if success:
        await callback.message.delete()
        await callback.message.answer(
            text=response,
            reply_markup=main_actions_keyboard(user.role),
        )
    else:
        await callback.message.answer(
            text=response,
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await state.clear()


@admin.callback_query(F.data == Callbacks.cancel_primary_action_callback)
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
