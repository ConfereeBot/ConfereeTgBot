from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.database.db_operations.tag_db_operations import update_tag_in_db
from app.database.db_operations.user_db_operations import get_user_by_telegram_tag
from app.keyboards import (
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.admin.admin import admin  # Импортируем роутер admin
from app.roles.user.callbacks_enum import Callbacks


class TagEditingStates(StatesGroup):
    waiting_for_new_name = State()


async def on_edit_tag_clicked(callback: CallbackQuery, state: FSMContext, tag_id: str):
    text = "Введите новое имя для тега. \nОно должно быть длиной не более 32 символов"
    reply_markup = await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
    await callback.message.edit_text(text=text, reply_markup=reply_markup)
    await state.update_data(tag_id=tag_id)
    await state.set_state(TagEditingStates.waiting_for_new_name)
    await callback.answer()


@admin.callback_query(F.data.startswith(Callbacks.tag_edit_callback))
async def on_tag_edit_callback(callback: CallbackQuery, state: FSMContext):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    await on_edit_tag_clicked(callback, state, tag_id)


@admin.message(TagEditingStates.waiting_for_new_name)
async def process_tag_edit(message: Message, state: FSMContext):
    new_name = message.text.strip()
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    if len(new_name) > 32:
        await message.answer(
            text="Новое имя слишком длинное! Максимум 32 символа. \nВведите новое имя:",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
        )
        return
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    if not tag_id:
        await message.answer("Ошибка: тег не найден!")
        await state.clear()
        return
    success, response = await update_tag_in_db(tag_id, new_name)
    if success:
        await message.answer(
            text=response,
            reply_markup=main_actions_keyboard(user.role)
        )
        await state.clear()
    else:
        await message.answer(
            text=response,
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
        )
