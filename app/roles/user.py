import os

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.config import messages as msg
from app.config.roles import Role
from app.filters import RoleFilter
from app.keyboards import (
    choose_recordings_search_method_keyboard as recordings_keyboard,
)
from app.keyboards import inline_admin_list, inline_tag_list
from app.keyboards import main as main_keyboard
from app.keyboards import manage_tag_inline_keyboard
from app.utils import setup_logger

logger = setup_logger(__name__)

user = Router()
user.message.filter(RoleFilter(Role.USER))


@user.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("cmd_start")
    await message.answer_photo(
        photo=FSInputFile(os.path.join(os.getcwd(), "app", "config", "images", "logo.webp")),
        caption=msg.START.format(name=message.from_user.first_name),
        reply_markup=main_keyboard,
    )


@user.message(F.text == "📥 Получить запись")
async def get_recording(message: Message):
    logger.info("get_recordings_call")
    await message.answer(
        text="Как вы хотите найти запись: по тегу или по ссылке?",
        reply_markup=recordings_keyboard,
    )


@user.message(F.text == "🗂️ Управление тегами")
async def manage_tags(message: Message):
    logger.info("manage_tags_call")
    await message.answer(
        text="Выберите тег или создайте новый",
        reply_markup=await inline_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_tags_management_mode_callback",
            on_item_add_clicked_callback="on_tag_add_clicked_in_tags_management_mode_callback",
            on_cancel_clicked_callback="on_cancel_primary_callback",
        ),
    )


@user.message(F.text == "🎥 Записать")
async def record_meeting(message: Message):
    logger.info("manage_tags_call")
    await message.answer(
        text="Выберите тег или создайте новый",
        reply_markup=await inline_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_recording_mode_callback",
            on_item_add_clicked_callback="on_tag_add_clicked_in_recording_mode_callback",
            on_cancel_clicked_callback="on_cancel_primary_callback",
        ),
    )


@user.message(F.text == "👨🏻‍💻 Управление админами")
async def manage_admins(message: Message):
    logger.info("manage_admins_call")
    await message.answer(
        text="Выберите админа или создайте новый",
        reply_markup=await inline_admin_list(),
    )


@user.callback_query(F.data == "get_recording_by_tag")
async def get_recording_by_tag(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите нужный тег",
        reply_markup=await inline_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_search_mode",
            on_item_add_clicked_callback="on_tag_clicked_in_search_mode",
            on_cancel_clicked_callback="on_cancel_primary_callback",
        ),
    )


@user.callback_query(F.data == "on_tag_clicked_in_recording_mode_callback")
async def on_tag_clicked_in_recording_mode_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo


@user.callback_query(F.data == "on_tag_clicked_in_tags_management_mode_callback")
async def on_tag_clicked_in_tags_management_mode_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите, что вы хотите сделать с тегом",
        reply_markup=manage_tag_inline_keyboard,
    )


@user.callback_query(F.data == "on_tag_edit_callback")
async def on_tag_edit_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo implement edit logic


@user.callback_query(F.data == "on_tag_delete_callback")
async def on_tag_delete_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo implement edit logic


@user.callback_query(F.data == "on_cancel_tag_action_callback")
async def on_cancel_tag_action_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите нужный тег",
        reply_markup=await inline_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_tags_management_mode_callback",
            on_item_add_clicked_callback="manage_tags_call",
            on_cancel_clicked_callback="on_cancel_primary_callback",
        ),
    )


@user.callback_query(F.data == "on_cancel_primary_callback")
async def on_cancel_primary_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой",
    )


@user.callback_query(F.data == "on_cancel_tag_select_for_search_callback")
async def on_cancel_tag_select_for_recording_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите тег или создайте новый",
        reply_markup=await inline_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_tags_management_mode_callback",
            on_item_add_clicked_callback="on_tag_add_clicked_in_tags_management_mode_callback",
            on_cancel_clicked_callback="on_cancel_primary_callback",
        ),
    )
