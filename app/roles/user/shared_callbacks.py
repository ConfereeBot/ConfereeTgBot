import enum

from app.roles.user.user_cmds import user, logger
from aiogram import F
from aiogram.types import CallbackQuery


class Callbacks(str, enum.Enum):
    cancel_primary_action_callback = "on_cancel_primary_callback"
    cancel_tag_action_callback = "on_cancel_tag_action_callback"
    tag_delete_callback = "on_tag_delete_callback"
    tag_edit_callback = "on_tag_edit_callback"
    tag_create_callback = "on_tag_create_callback"
    tag_clicked_in_tags_management_mode_callback = "on_tag_clicked_in_tags_management_mode_callback"
    tag_clicked_in_recording_mode_callback = "on_tag_clicked_in_recording_mode_callback"


@user.callback_query(
    F.data == Callbacks.cancel_primary_action_callback
)
async def on_cancel_primary_callback(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой",
    )
