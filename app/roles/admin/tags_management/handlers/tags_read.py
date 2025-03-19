from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import labels
from app.database.tag_db_operations import (
    get_tag_by_id,
    unarchive_tag_in_db,
)
from app.database.user_db_operations import get_user_by_telegram_tag
from app.keyboards import (
    inline_active_tag_list,
    inline_archived_tag_actions,
    inline_archived_tag_list,
    main_actions_keyboard,
    manage_tag_inline_keyboard,
)
from app.roles.admin.admin import admin  # Импортируем роутер admin
from app.roles.user.callbacks_enum import Callbacks
from app.utils.logger import logger


class TagManagementStates(StatesGroup):
    waiting_for_delete_confirmation = State()


async def manage_tags(event: Message | CallbackQuery, state: FSMContext = None):
    logger.info("manage_tags_call")
    if state:
        await state.clear()
    telegram_tag = f"@{event.from_user.username}" if event.from_user.username else f"@{event.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    text = "Выберите тег или создайте новый:"
    reply_markup = await inline_active_tag_list(
        on_item_clicked_callback=Callbacks.tag_clicked_manage_callback,
        on_item_create_clicked_callback=Callbacks.tag_create_callback,
        on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
        on_archived_clicked_callback=Callbacks.show_archived_in_manage_mode,
    )
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=reply_markup)
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=reply_markup)
        await event.answer("")


@admin.message(F.text == labels.MANAGE_TAGS)
async def handle_manage_tags_command(message: Message):
    await manage_tags(message)


@admin.callback_query(F.data == Callbacks.show_archived_in_manage_mode)
async def on_show_archived_in_manage_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Выберите тег из архива:",
        reply_markup=await inline_archived_tag_list(
            on_item_clicked_callback=Callbacks.archived_tag_clicked_manage_callback,
            on_back_clicked_callback=Callbacks.return_back_from_archived_callback,
        ),
    )
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.archived_tag_clicked_manage_callback))
async def on_archived_tag_clicked_in_manage_mode(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return
    await callback.message.edit_text(
        text=f"Выберите действие над архивированным тегом '{tag.name}':",
        reply_markup=await inline_archived_tag_actions(
            on_unarchive_clicked_callback=f"{Callbacks.unarchive_tag_clicked_callback}:{tag_id}",
            on_delete_clicked_callback=f"{Callbacks.tag_delete_callback}:{tag_id}",
            on_back_clicked_callback=f"{Callbacks.return_back_from_archived_tag_actions_callback}:{tag_id}",
        ),
    )
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.unarchive_tag_clicked_callback))
async def unarchive_tag_clicked_callback(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    success, response = await unarchive_tag_in_db(tag_id)
    await callback.message.answer(text=response, reply_markup=main_actions_keyboard(user.role))
    await callback.message.delete()
    await callback.answer("")


@admin.callback_query(F.data == Callbacks.return_back_from_archived_callback)
async def return_back_from_archived(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)


@admin.callback_query(F.data.startswith(Callbacks.tag_clicked_manage_callback))
async def tag_clicked_manage_callback(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return
    await callback.answer("")
    await callback.message.edit_text(
        text=f"Выберите, что вы хотите сделать с тегом '{tag.name}'",
        reply_markup=manage_tag_inline_keyboard(tag_id),
    )


@admin.callback_query(F.data.startswith(Callbacks.return_back_from_archived_tag_actions_callback))
async def on_return_back_from_archived_tag_actions(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Выберите тег из архива:",
        reply_markup=await inline_archived_tag_list(
            on_item_clicked_callback=Callbacks.archived_tag_clicked_manage_callback,
            on_back_clicked_callback=Callbacks.return_back_from_archived_callback,
        ),
    )
    await callback.answer("")
