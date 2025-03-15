from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import labels
from app.config.config import OWNERS
from app.database.user_db_operations import (
    add_or_update_user_to_admin,
    demote_admin_to_user,
    get_user_by_id,
)
from app.keyboards import (
    inline_admin_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user
from app.utils.logger import logger


class AdminManagementStates(StatesGroup):
    waiting_for_admin_username = State()


def is_valid_telegram_username(username: str) -> bool:
    """
    Validates Telegram-username.
    Username must:
    - Start with @
    - Have 5 or more symbols
    - No digit or _ after @
    - Have only letters (a-z, A-Z), digits (0-9) and _
    """
    return (
            username.startswith("@")
            and len(username) >= 5
            and not username[1].isdigit()
            and username[1] != "_"
            and all(c.isalnum() or c == "_" for c in username[1:])
    )


@user.message(F.text == labels.MANAGE_ADMINS)
async def manage_admins(message: Message):
    logger.info("manage_admins_call")
    await message.answer(
        text="Выберите админа или создайте нового:",
        reply_markup=await inline_admin_list(
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
        ),
    )


async def on_add_admin_clicked(callback: CallbackQuery, state: FSMContext):
    text = "Введите Telegram-тег нового админа в формате '@username':"
    reply_markup = await inline_single_cancel_button(Callbacks.cancel_primary_action_callback)
    await callback.message.edit_text(text=text, reply_markup=reply_markup)
    await state.set_state(AdminManagementStates.waiting_for_admin_username)
    await callback.answer()


@user.callback_query(F.data == Callbacks.add_admin_callback)
async def handle_add_admin_callback(callback: CallbackQuery, state: FSMContext):
    await on_add_admin_clicked(callback, state)


@user.message(AdminManagementStates.waiting_for_admin_username)
async def process_admin_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not is_valid_telegram_username(username):
        await message.answer(
            text="Некорректный формат! Используйте '@username'\n"
                 "(минимум 5 символов, только буквы, цифры и _, "
                 "не начинается с цифры или _).\nВведите снова:",
            reply_markup=await inline_single_cancel_button(
                Callbacks.cancel_primary_action_callback
            ),
        )
        return
    if username in OWNERS:
        await message.answer(
            text=f"Пользователь '{username}' является владельцем и не может быть изменён!",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback)
        )
        return
    success, response = await add_or_update_user_to_admin(username)
    if success:
        await message.answer(text=response, reply_markup=main_actions_keyboard)
        await state.clear()
    else:
        await message.answer(
            text=response,
            reply_markup=await inline_single_cancel_button(
                Callbacks.cancel_primary_action_callback
            ),
        )
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)


@user.callback_query(F.data.startswith("admin_clicked"))
async def on_admin_clicked(callback: CallbackQuery):
    try:
        user_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: пользователь не выбран!", show_alert=True)
        return
    user = await get_user_by_id(user_id)
    if not user or user.role != "admin":
        await callback.answer("Ошибка: админ не найден в базе данных!", show_alert=True)
        print(f"Ошибка: админ не найден с id {user_id}!")
        return
    text = (
        f"Username админа: {user.telegram_tag}\n"
        "Админ имеет права на управление тегами (их добавление, изменение, архивацию и удаление)."
    )
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Понизить до пользователя",
                    callback_data=f"{Callbacks.admin_delete_callback}:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩ Вернуться назад",
                    callback_data=Callbacks.return_to_admin_list_callback,
                )
            ],
        ]
    )
    await callback.message.edit_text(text=text, reply_markup=reply_markup)
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.admin_delete_callback))
async def on_admin_delete_callback(callback: CallbackQuery):
    try:
        user_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: пользователь не выбран!", show_alert=True)
        return
    success, response = await demote_admin_to_user(user_id)
    await callback.message.answer(text=response, reply_markup=main_actions_keyboard)
    await callback.message.delete()
    await callback.answer("")


@user.callback_query(F.data == Callbacks.return_to_admin_list_callback)
async def on_return_to_admin_list(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Выберите админа или создайте нового:",
        reply_markup=await inline_admin_list(
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
        ),
    )
    await callback.answer("")
