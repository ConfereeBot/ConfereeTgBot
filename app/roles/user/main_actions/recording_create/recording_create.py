from aiogram import F
from aiogram.types import CallbackQuery, Message

from app.config import labels
from app.keyboards import inline_active_tag_list, manage_tag_inline_keyboard
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import logger, user


@user.message(F.text == labels.RECORD)
async def record_meeting(message: Message):
    logger.info("manage_tags_call")
    await message.answer(
        text="Выберите тег для записи:",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback="on_tag_clicked_in_recording_mode_callback",
            on_item_create_clicked_callback="on_tag_add_clicked_in_recording_mode_callback",
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
        ),
    )


@user.callback_query(F.data == Callbacks.tag_clicked_in_recording_mode_callback)
async def on_tag_clicked_in_recording_mode_callback(callback: CallbackQuery):
    await callback.answer("")
    # todo
