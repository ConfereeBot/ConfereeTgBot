from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.keyboards import (
    inline_tag_list, manage_tag_inline_keyboard, inline_single_cancel_button, main_actions_keyboard,
)
from app.roles.user.main_actions.tags_management.tags_db_operations import add_tag_to_db
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger

logger.info("Starting to register handlers in tags_management.py")  # Отладка


class TagCreationStates(StatesGroup):
    waiting_for_tag_name = State()
    choosing_tag = State()


# Универсальная функция manage_tags
async def manage_tags(event: Message | CallbackQuery, state: FSMContext = None):
    logger.info("manage_tags_call")
    if state:
        await state.clear()
    text = "Выберите тег или создайте новый:"
    reply_markup = await inline_tag_list(
        on_item_clicked_callback=Callbacks.tag_clicked_in_tags_management_mode_callback,
        on_item_create_clicked_callback=Callbacks.tag_create_callback,
        on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
    )
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=reply_markup)
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=reply_markup)
        await event.answer("")


async def on_create_tag_clicked(event: Message | CallbackQuery, state: FSMContext):
    text = "Введите название нового тега. \nОно должно быть длиной не более 32 символов"
    reply_markup = await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=reply_markup)
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=reply_markup)
        await event.answer()
    await state.set_state(TagCreationStates.waiting_for_tag_name)


@user.message(F.text == "🗂️ Управление тегами")
async def handle_manage_tags_command(message: Message):
    await manage_tags(message)


@user.callback_query(F.data == Callbacks.tag_create_callback)
async def handle_create_tag_callback(callback: CallbackQuery, state: FSMContext):
    await on_create_tag_clicked(callback, state)


@user.callback_query(F.data == Callbacks.tag_clicked_in_tags_management_mode_callback)
async def on_tag_clicked_in_tags_management_mode_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите, что вы хотите сделать с тегом",
        reply_markup=manage_tag_inline_keyboard
    )


@user.callback_query(F.data == Callbacks.tag_edit_callback)
async def on_tag_edit_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo implement edit logic


@user.callback_query(F.data == Callbacks.tag_delete_callback)
async def on_tag_delete_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo implement edit logic


@user.message(TagCreationStates.waiting_for_tag_name)
async def process_tag_name(message: Message, state: FSMContext):
    tag_name = message.text.strip()
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
            reply_markup=main_actions_keyboard
        )
        await state.clear()
    else:
        await message.answer(
            text=response,
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
        )


@user.callback_query(F.data == Callbacks.cancel_tag_naming_callback)
async def on_cancel_tag_naming(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)


@user.callback_query(F.data == Callbacks.cancel_tag_manage_callback)
async def on_cancel_tag_naming(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)
