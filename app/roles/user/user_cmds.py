import os

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from app.config import messages as msg
from app.config.roles import Role
from app.database.user_db_operations import handle_user_on_start
from app.keyboards import main_actions_keyboard
from app.utils.logger import logger

user_router = Router()


@user_router.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("cmd_start")
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    telegram_id = message.from_user.id

    try:
        user = await handle_user_on_start(telegram_tag, telegram_id)
    except Exception as e:
        logger.error(f"Ошибка при обработке пользователя '{telegram_tag}': {str(e)}")
        await message.answer(
            text=f"Ошибка при регистрации: {str(e)}",
            reply_markup=main_actions_keyboard(Role.USER)
        )
        return

    await message.answer_photo(
        photo=FSInputFile(os.path.join(os.getcwd(), "app", "config", "images", "logo.webp")),
        caption=msg.START.format(name=message.from_user.first_name),
        reply_markup=main_actions_keyboard(user.role)
    )
