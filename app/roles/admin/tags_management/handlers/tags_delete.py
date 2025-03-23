from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.database.db_operations.tag_db_operations import archive_tag_in_db, get_tag_by_id, delete_tag_from_db
from app.database.db_operations.user_db_operations import get_user_by_telegram_tag
from app.keyboards import main_actions_keyboard, tag_deletion_confirmation_keyboard, inline_archived_tag_actions
from app.roles.admin.admin import admin  # Импортируем роутер admin
from app.roles.admin.tags_management.handlers.tags_read import TagManagementStates, manage_tags
from app.roles.user.callbacks_enum import Callbacks


@admin.callback_query(F.data.startswith(Callbacks.tag_archive_callback))
async def on_tag_archive_callback(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    success, response = await archive_tag_in_db(tag_id)
    await callback.message.answer(text=response, reply_markup=main_actions_keyboard(user.role))
    await callback.message.delete()
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.tag_delete_callback))
async def on_tag_delete_callback(callback: CallbackQuery, state: FSMContext):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return
    await state.update_data(tag_id=tag_id)
    await state.set_state(TagManagementStates.waiting_for_delete_confirmation)
    await callback.message.edit_text(
        text=f"❗ Требуется подтверждение опасного действия\n\nВы точно хотите удалить тег '{tag.name}' и все связанные с ним записи навсегда?",
        reply_markup=tag_deletion_confirmation_keyboard,
    )
    await callback.answer("")


@admin.callback_query(
    F.data == Callbacks.cancel_deletion,
    TagManagementStates.waiting_for_delete_confirmation,
    )
async def on_cancel_delete(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    if not tag_id:
        await callback.answer("Ошибка: тег не найден!", show_alert=True)
        await state.clear()
        return
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        await state.clear()
        return
    await callback.message.edit_text(
        text=f"Выберите действие над архивированным тегом '{tag.name}':",
        reply_markup=await inline_archived_tag_actions(
            on_unarchive_clicked_callback=f"{Callbacks.unarchive_tag_clicked_callback}:{tag_id}",
            on_delete_clicked_callback=f"{Callbacks.tag_delete_callback}:{tag_id}",
            on_back_clicked_callback=f"{Callbacks.return_back_from_archived_tag_actions_callback}:{tag_id}",
        ),
    )
    await state.clear()
    await callback.answer("")


@admin.callback_query(
    F.data == Callbacks.confirm_deletion,
    TagManagementStates.waiting_for_delete_confirmation,
    )
async def on_confirm_delete(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    if not tag_id:
        await callback.answer("Ошибка: тег не найден!", show_alert=True)
        await state.clear()
        return
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    success, response = await delete_tag_from_db(tag_id)
    await callback.message.answer(text=response, reply_markup=main_actions_keyboard(user.role))
    await callback.message.delete()
    await state.clear()
    await callback.answer("")


@admin.callback_query(F.data == Callbacks.cancel_tag_manage_callback)
async def on_cancel_tag_manage(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)
