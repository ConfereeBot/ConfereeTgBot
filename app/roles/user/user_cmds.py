import os

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from app.config import messages as msg
from app.config.roles import Role
from app.filters import RoleFilter
from app.keyboards import (
    main as main_keyboard,
)
from app.utils import setup_logger

logger = setup_logger(__name__)

user = Router()
user.message.filter(RoleFilter(Role.USER))
user.callback_query.filter(RoleFilter(Role.USER))


@user.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("cmd_start")
    await message.answer_photo(
        photo=FSInputFile(os.path.join(os.getcwd(), "app", "config", "images", "logo.webp")),
        caption=msg.START.format(name=message.from_user.first_name),
        reply_markup=main_keyboard
    )
