import os

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, Message

from app.config import messages as msg
from app.config.roles import Role
from app.filters import RoleFilter
from app.utils import setup_logger

from app.keyboards import (
    main as main_keyboard,
    choose_recordings_search_method_keyboard as recordings_keyboard,
    inline_tag_list_for_edit,
    inline_tag_list_for_recording,
    inline_admin_list,
)

logger = setup_logger(__name__)

user = Router()
user.message.filter(RoleFilter(Role.USER))


@user.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("cmd_start")
    await message.answer_photo(
        photo=FSInputFile(os.path.join(os.getcwd(), "app", "config", "images", "logo.webp")),
        caption=msg.START.format(name=message.from_user.first_name),
        reply_markup=main_keyboard
    )


@user.message(F.text == "📥 Получить запись")
async def get_recording(message: Message):
    logger.info("get_recordings_call")
    await message.answer(
        text="Как вы хотите найти запись: по тегу или по ссылке?",
        reply_markup=recordings_keyboard
    )


@user.message(F.text == "🗂️ Управление тегами")
async def get_recording(message: Message):
    logger.info("manage_tags_call")
    await message.answer(
        text="Выберите тег или создайте новый",
        reply_markup=await inline_tag_list_for_edit()
    )


@user.message(F.text == "🎥 Записать")
async def get_recording(message: Message):
    logger.info("manage_tags_call")
    await message.answer(
        text="Выберите тег или создайте новый",
        reply_markup=await inline_tag_list_for_recording()
    )

@user.message(F.text == "👨🏻‍💻 Управление админами")
async def get_recording(message: Message):
    logger.info("manage_admins_call")
    await message.answer(
        text="Выберите админа или создайте новый",
        reply_markup=await inline_admin_list()
    )
