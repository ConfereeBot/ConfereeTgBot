from app.keyboards import main_actions_keyboard
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger
from aiogram import F
from aiogram.types import CallbackQuery


@user.callback_query(
    F.data == Callbacks.cancel_primary_action_callback
)
async def on_cancel_primary_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.delete()  # delete prev message
    await callback.message.answer(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой",
        reply_markup=main_actions_keyboard
    )
