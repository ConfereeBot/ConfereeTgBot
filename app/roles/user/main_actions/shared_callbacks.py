from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.database.user_db_operations import get_user_by_telegram_tag
from app.keyboards import main_actions_keyboard
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user_router
from app.utils.logger import logger


@user_router.callback_query(F.data == Callbacks.cancel_primary_action_callback)
async def on_cancel_primary_callback(callback: CallbackQuery, state: FSMContext):
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        logger.error(f"Пользователь с тегом {telegram_tag} не найден при отмене действия")
        return
    await callback.answer("")
    await callback.message.delete()
    await callback.message.answer(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой",
        reply_markup=main_actions_keyboard(user.role)
    )
    await state.clear()
