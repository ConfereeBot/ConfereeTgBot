import os

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from app.config import messages as msg
from app.config.roles import Role
from app.database.user_db_operations import add_user_if_not_exists, get_user_by_telegram_tag
from app.keyboards import main_actions_keyboard
from app.utils.logger import logger

user = Router()


# Убираем глобальный фильтр для коллбэков
# user.callback_query.filter(RoleFilter(Role.USER))


@user.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("cmd_start")
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"

    # Проверяем, есть ли пользователь в базе
    db_user = await get_user_by_telegram_tag(telegram_tag)
    if not db_user:
        # Если пользователя нет, добавляем его с ролью USER
        success, response, user = await add_user_if_not_exists(telegram_tag)
        if not success:
            logger.error(f"Ошибка при добавлении пользователя '{telegram_tag}': {response}")
            await message.answer(
                text=f"Ошибка при регистрации: {response}",
                reply_markup=main_actions_keyboard(Role.USER)
            )
            return
    else:
        user = db_user

    await message.answer_photo(
        photo=FSInputFile(os.path.join(os.getcwd(), "app", "config", "images", "logo.webp")),
        caption=msg.START.format(name=message.from_user.first_name),
        reply_markup=main_actions_keyboard(user.role)
    )
