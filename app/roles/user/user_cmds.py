import os

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from app.config import messages as msg
from app.config.roles import Role
from app.database.user_db_operations import add_user_if_not_exists
from app.filters import RoleFilter
from app.keyboards import (
    main_actions_keyboard as main_keyboard,
)
from app.utils.logger import logger

user = Router()
user.message.filter(RoleFilter(Role.USER))
user.callback_query.filter(RoleFilter(Role.USER))


@user.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("cmd_start")
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"

    success, response, user = await add_user_if_not_exists(telegram_tag)
    if not success:
        logger.error(f"Ошибка при добавлении пользователя '{telegram_tag}': {response}")
        await message.answer(
            text=f"Ошибка при регистрации: {response}",
            reply_markup=main_keyboard
        )
        return

    await message.answer_photo(
        photo=FSInputFile(os.path.join(os.getcwd(), "app", "config", "images", "logo.webp")),
        caption=msg.START.format(name=message.from_user.first_name),
        reply_markup=main_keyboard
    )
