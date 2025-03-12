from aiogram import F
from aiogram.types import CallbackQuery, Message

from app.config import labels
from app.keyboards import (
    choose_recordings_search_method_keyboard as recordings_keyboard,
)
from app.keyboards import inline_active_tag_list
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import logger, user


@user.message(F.text == labels.GET_RECORD)
async def get_recording(message: Message):
    logger.info("get_recordings_call")
    await message.answer(
        text="Как вы хотите найти запись: по тегу или по ссылке?",
        reply_markup=recordings_keyboard,
    )


@user.callback_query(F.data == "get_recording_by_tag")
async def get_recording_by_tag(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите нужный тег",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_search_mode",
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
        ),
    )


@user.callback_query(F.data == "on_cancel_tag_select_for_search_callback")
async def on_cancel_tag_select_for_recording_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите тег или создайте новый",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_recording_mode_callback,
            on_item_create_clicked_callback="on_tag_add_clicked_in_tags_management_mode_callback",
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
        ),
    )
