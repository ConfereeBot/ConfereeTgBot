from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.keyboards import (
    inline_tag_list, manage_tag_inline_keyboard, inline_single_cancel_button, main_actions_keyboard,
)
from app.roles.user.main_actions.tags_management.db.tags_db_operations import add_tag_to_db
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger


class TagEditingStates(StatesGroup):
    waiting_for_new_name = State()


async def on_edit_tag_clicked(callback: CallbackQuery, state: FSMContext, tag_id: str):
    text = "Введите новое имя для тега. \nОно должно быть длиной не более 32 символов"
    reply_markup = await inline_single_cancel_button(Callbacks.cancel_tag_naming_callback)
    await callback.message.edit_text(text=text, reply_markup=reply_markup)
    await state.update_data(tag_id=tag_id)
    await state.set_state(TagEditingStates.waiting_for_new_name)
    await callback.answer()


@user.callback_query(F.data == Callbacks.tag_edit_callback)
async def on_tag_edit_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo implement edit logic
