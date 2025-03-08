from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.keyboards import (
    inline_tag_list, manage_tag_inline_keyboard,
)
from app.roles.user.main_actions.tags_management.tags_db_operations import add_tag_to_db
from app.roles.user.shared_callbacks import Callbacks
from app.roles.user.user_cmds import user, logger

logger.info("Starting to register handlers in tags_management.py")  # Отладка


class TagCreationStates(StatesGroup):
    waiting_for_tag_name = State()


# @user.callback_query(F.text == Callbacks.cancel_tag_action_callback)
@user.message(F.text == "🗂️ Управление тегами")
async def manage_tags(message: Message):
    logger.info("manage_tags_call")
    await message.answer(
        text="Выберите тег или создайте новый:",
        reply_markup=await inline_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_tags_management_mode_callback,
            on_item_create_clicked_callback=Callbacks.tag_create_callback,
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
        )
    )


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


@user.callback_query(F.data == Callbacks.tag_create_callback)
async def on_create_tag_clicked(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите название нового тега. Оно должно быть длиной не более 32 символов."
    )
    await state.set_state(TagCreationStates.waiting_for_tag_name)
    await callback.answer()


@user.message(TagCreationStates.waiting_for_tag_name)
async def process_tag_name(message: Message, state: FSMContext):
    tag_name = message.text.strip()
    if len(tag_name) > 32:
        await message.answer("Название тега слишком длинное! Максимум 32 символа.")
        return
    success, response = await add_tag_to_db(tag_name)
    await message.answer(response)
    await state.clear()
