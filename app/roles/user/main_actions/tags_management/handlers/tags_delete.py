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


@user.callback_query(F.data == Callbacks.tag_delete_callback)
async def on_tag_delete_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo implement edit logic
