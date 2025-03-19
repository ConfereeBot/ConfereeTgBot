from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.database.tag_db_operations import add_tag_to_db
from app.database.user_db_operations import get_user_by_telegram_tag
from app.keyboards import (
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.admin.admin import admin
from app.roles.user.callbacks_enum import Callbacks
from app.roles.admin.tags_management.handlers.tags_read import manage_tags


class TagCreationStates(StatesGroup):
    waiting_for_tag_name = State()


async def on_create_tag_clicked(event: Message | CallbackQuery, state: FSMContext):
    text = "Введите название нового тега. \nОно должно быть длиной не более 32 символов"
    reply_markup = await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=reply_markup)
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=reply_markup)
        await event.answer()
    await state.set_state(TagCreationStates.waiting_for_tag_name)


@admin.callback_query(F.data == Callbacks.tag_create_callback)
async def handle_create_tag_callback(callback: CallbackQuery, state: FSMContext):
    await on_create_tag_clicked(callback, state)


@admin.message(TagCreationStates.waiting_for_tag_name)
async def process_tag_name(message: Message, state: FSMContext):
    tag_name = message.text.strip()
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    if len(tag_name) > 32:
        await message.answer(
            text="Название тега слишком длинное! Максимум 32 символа. \nВведите новое название:",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
        )
        return
    success, response = await add_tag_to_db(tag_name)
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


@admin.callback_query(F.data == Callbacks.cancel_tag_naming_callback)
async def on_cancel_tag_naming(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)
