from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from bson import ObjectId

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
    waiting_for_start_date = State()
    waiting_for_timezone = State()
    waiting_for_recurrence = State()
    waiting_for_periodicity = State()


@user.message(F.text == labels.RECORD)
async def start_recording(message: Message, state: FSMContext):
    """Start the recording creation process by selecting a tag."""
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


@user.callback_query(F.data.startswith(Callbacks.tag_clicked_in_recording_mode_callback))
async def process_tag_for_recording(callback: CallbackQuery, state: FSMContext):
    """Process the selected tag and ask for the conference link."""
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return

    await state.update_data(tag_id=tag_id)
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=Callbacks.back_to_tag_in_create_conference_mode)]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_meet_link)
    await callback.answer("")


@user.callback_query(F.data == Callbacks.back_to_tag_in_create_conference_mode, RecordingCreateStates.waiting_for_meet_link)
async def back_to_tag_from_link(callback: CallbackQuery, state: FSMContext):
    """Return to tag selection from link input."""
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


@user.message(RecordingCreateStates.waiting_for_meet_link)
async def process_meet_link_for_recording(message: Message, state: FSMContext):
    """Process the conference link and ask for the start date."""
    meet_link = message.text.strip()
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")

    if not tag_id:
        await message.answer(
            text="Ошибка: тег не выбран! Попробуйте начать заново.",
            reply_markup=main_actions_keyboard,
        )
        await state.clear()
        return

    await state.update_data(meet_link=meet_link)
    await message.answer(
        text="Введите дату начала конференции в формате 'ДЕНЬ.МЕСЯЦ.ГОД ЧАСЫ:МИНУТЫ:СЕКУНДЫ' (например, 15.03.2025 14:30:00):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=Callbacks.back_to_tag_in_create_conference_mode)]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_start_date)


@user.callback_query(F.data == Callbacks.back_to_tag_in_create_conference_mode, RecordingCreateStates.waiting_for_start_date)
async def back_to_tag_from_date(callback: CallbackQuery, state: FSMContext):
    """Return to tag selection from start date input."""
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


@user.message(RecordingCreateStates.waiting_for_start_date)
async def process_start_date(message: Message, state: FSMContext):
    """Process the start date and ask for the timezone."""
    try:
        start_date_str = message.text.strip()
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y %H:%M:%S")
        timestamp = int(start_date.timestamp())  # Convert to Unix timestamp
    except ValueError:
        await message.answer(
            text="Ошибка: неверный формат даты! Используйте 'ДЕНЬ.МЕСЯЦ.ГОД ЧАСЫ:МИНУТЫ:СЕКУНДЫ' (например, 15.03.2025 14:30:00). Повторите ввод:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_to_link")]
            ]),
        )
        return

    await state.update_data(timestamp=timestamp)
    await message.answer(
        text="Укажите тайм-зону относительно UTC (например, +3 или -5):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_date")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_timezone)


@user.callback_query(F.data == "back_to_link", RecordingCreateStates.waiting_for_start_date)
async def back_to_link_from_date(callback: CallbackQuery, state: FSMContext):
    """Return to link input from start date."""
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=Callbacks.back_to_tag_in_create_conference_mode)]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_meet_link)
    await callback.answer("")


@user.message(RecordingCreateStates.waiting_for_timezone)
async def process_timezone(message: Message, state: FSMContext):
    """Process the timezone and ask about recurrence."""
    timezone_str = message.text.strip()
    try:
        timezone = int(timezone_str)  # Expecting something like +3 or -5
        if not -12 <= timezone <= 14:  # Reasonable timezone range
            raise ValueError
    except ValueError:
        await message.answer(
            text="Ошибка: неверный формат тайм-зоны! Введите число от -12 до +14 (например, +3 или -5). Повторите ввод:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_to_date")]
            ]),
        )
        return

    await state.update_data(timezone=timezone)
    await message.answer(
        text="Это регулярная встреча?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="recurrence_yes"),
             InlineKeyboardButton(text="Нет", callback_data="recurrence_no")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_date")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_recurrence)


@user.callback_query(F.data == "back_to_date", RecordingCreateStates.waiting_for_timezone)
async def back_to_date_from_timezone(callback: CallbackQuery, state: FSMContext):
    """Return to start date input from timezone."""
    await callback.message.edit_text(
        text="Введите дату начала конференции в формате 'ДЕНЬ.МЕСЯЦ.ГОД ЧАСЫ:МИНУТЫ:СЕКУНДЫ' (например, 15.03.2025 14:30:00):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_link")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_start_date)
    await callback.answer("")


@user.callback_query(F.data.startswith("recurrence_"), RecordingCreateStates.waiting_for_recurrence)
async def process_recurrence(callback: CallbackQuery, state: FSMContext):
    """Process recurrence choice and either ask for periodicity or finish."""
    recurrence = callback.data == "recurrence_yes"
    await state.update_data(recurrence=recurrence)

    if recurrence:
        await callback.message.edit_text(
            text="С какой периодичностью повторяется встреча?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1 неделя", callback_data="period_1"),
                 InlineKeyboardButton(text="2 недели", callback_data="period_2")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_timezone")]
            ]),
        )
        await state.set_state(RecordingCreateStates.waiting_for_periodicity)
    else:
        await finish_recording(callback, state)
    await callback.answer("")


@user.callback_query(F.data == "back_to_date", RecordingCreateStates.waiting_for_recurrence)
async def back_to_date_from_recurrence(callback: CallbackQuery, state: FSMContext):
    """Return to timezone input from recurrence."""
    await callback.message.edit_text(
        text="Укажите тайм-зону относительно UTC (например, +3 или -5):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_date")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_timezone)
    await callback.answer("")


@user.callback_query(F.data.startswith("period_"), RecordingCreateStates.waiting_for_periodicity)
async def process_periodicity(callback: CallbackQuery, state: FSMContext):
    """Process periodicity choice and finish recording creation."""
    periodicity = int(callback.data.split("_")[1])  # Extract 1 or 2
    await state.update_data(periodicity=periodicity)
    await finish_recording(callback, state)
    await callback.answer("")


@user.callback_query(F.data == "back_to_timezone", RecordingCreateStates.waiting_for_periodicity)
async def back_to_timezone_from_periodicity(callback: CallbackQuery, state: FSMContext):
    """Return to recurrence question from periodicity."""
    await callback.message.edit_text(
        text="Это регулярная встреча?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="recurrence_yes"),
             InlineKeyboardButton(text="Нет", callback_data="recurrence_no")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_date")]
        ]),
    )
    await state.set_state(RecordingCreateStates.waiting_for_recurrence)
    await callback.answer("")


async def finish_recording(callback: CallbackQuery, state: FSMContext):
    """Finish the recording creation process and save to database."""
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    meet_link = state_data.get("meet_link")
    timestamp = state_data.get("timestamp")
    timezone = state_data.get("timezone")
    recurrence = state_data.get("recurrence")
    periodicity = state_data.get("periodicity", None)  # None if not recurrent

    success, response, conference_id = await add_conference_to_db(
        meet_link=meet_link,
        tag_id=ObjectId(tag_id),
        timestamp=timestamp,
        timezone=timezone,
        periodicity=periodicity if recurrence else None
    )

    if success:
        await callback.message.answer(
            text=f"{response}\nID конференции: {conference_id}\nЗаписей пока нет.",
            reply_markup=main_actions_keyboard,
        )
    else:
        await callback.message.answer(
            text=response,
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
