from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from aiogram.fsm.state import State, StatesGroup
from app.database.tag_db_operations import unarchive_tag_in_db, delete_tag_from_db, archive_tag_in_db, get_tag_by_id
from app.keyboards import inline_active_tag_list, manage_tag_inline_keyboard, inline_archived_tag_list, \
    inline_archived_tag_actions, main_actions_keyboard, inline_single_cancel_button, tag_deletion_confirmation_keyboard
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger


# Определяем состояния
class TagManagementStates(StatesGroup):
    waiting_for_delete_confirmation = State()  # Состояние для подтверждения удаления


# General
async def manage_tags(event: Message | CallbackQuery, state: FSMContext = None):
    logger.info("manage_tags_call")
    if state:
        await state.clear()
    text = "Выберите тег или создайте новый:"
    reply_markup = await inline_active_tag_list(
        on_item_clicked_callback=Callbacks.tag_clicked_manage_callback,
        on_item_create_clicked_callback=Callbacks.tag_create_callback,
        on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
        on_archived_clicked_callback=Callbacks.show_archived_in_manage_mode
    )
    print(f"Type of this is {type(Callbacks.cancel_primary_action_callback)}")
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=reply_markup)
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, reply_markup=reply_markup)
        await event.answer("")


@user.message(F.text == "🗂️ Управление тегами")
async def handle_manage_tags_command(message: Message):
    await manage_tags(message)


# Archive manage
@user.callback_query(
    F.data == Callbacks.show_archived_in_manage_mode
    or F.data == Callbacks.return_back_from_archived_tag_actions_callback
)
async def on_show_archived_in_manage_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Выберите тег из архива:",
        reply_markup=await inline_archived_tag_list(
            on_item_clicked_callback=Callbacks.archived_tag_clicked_manage_callback,
            on_back_clicked_callback=Callbacks.return_back_from_archived_callback,
        )
    )
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.archived_tag_clicked_manage_callback))
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
            on_back_clicked_callback=f"{Callbacks.return_back_from_archived_tag_actions_callback}:{tag_id}"
        )
    )
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.unarchive_tag_clicked_callback))
async def unarchive_tag_clicked_callback(callback: CallbackQuery):
    print(f"Received callback.data: {callback.data}")  # Отладка
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    success, response = await unarchive_tag_in_db(tag_id)
    await callback.message.answer(
        text=response,
        reply_markup=main_actions_keyboard
    )
    await callback.message.delete()
    await callback.answer("")


@user.callback_query(F.data == Callbacks.return_back_from_archived_callback)
async def return_back_from_archived(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)


# Usual tag manage
@user.callback_query(F.data.startswith(Callbacks.tag_clicked_manage_callback))
async def tag_clicked_manage_callback(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]  # Извлекаем tag_id
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
        reply_markup=manage_tag_inline_keyboard(tag_id)
    )


# Новый хэндлер для архивации
@user.callback_query(F.data.startswith(Callbacks.tag_archive_callback))
async def on_tag_archive_callback(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]  # Извлекаем tag_id
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    success, response = await archive_tag_in_db(tag_id)
    await callback.message.answer(
        text=response,
        reply_markup=main_actions_keyboard
    )
    await callback.message.delete()
    await callback.answer("")


# Callback для удаления тега
@user.callback_query(F.data.startswith(Callbacks.tag_delete_callback))
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
        text=f"Вы точно хотите удалить тег '{tag.name}' и все связанные с ним записи навсегда?",
        reply_markup=tag_deletion_confirmation_keyboard
    )
    await callback.answer("")


# Обработка отмены удаления
@user.callback_query(F.data == Callbacks.cancel_deletion, TagManagementStates.waiting_for_delete_confirmation)
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
            on_back_clicked_callback=f"{Callbacks.return_back_from_archived_tag_actions_callback}:{tag_id}"
        )
    )
    await state.clear()
    await callback.answer("")


# Обработка подтверждения удаления
@user.callback_query(F.data == Callbacks.confirm_deletion, TagManagementStates.waiting_for_delete_confirmation)
async def on_confirm_delete(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tag_id = state_data.get("tag_id")
    if not tag_id:
        await callback.answer("Ошибка: тег не найден!", show_alert=True)
        await state.clear()
        return
    success, response = await delete_tag_from_db(tag_id)
    await callback.message.answer(
        text=response,
        reply_markup=main_actions_keyboard
    )
    await callback.message.delete()
    await state.clear()
    await callback.answer("")


@user.callback_query(F.data == Callbacks.cancel_tag_manage_callback)
async def on_cancel_tag_manage(callback: CallbackQuery, state: FSMContext):
    await manage_tags(callback, state)
