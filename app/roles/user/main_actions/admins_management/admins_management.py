from aiogram import F
from aiogram.types import Message, CallbackQuery
from app.keyboards import inline_admin_list
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger

@user.message(F.text == "👨🏻‍💻 Управление админами")
async def manage_admins(message: Message):
    logger.info("manage_admins_call")
    await message.answer(
        text="Выберите админа или создайте нового:",
        reply_markup=await inline_admin_list(
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
        )
    )
