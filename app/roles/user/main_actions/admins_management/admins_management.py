from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery

from app.database.admin_db_operations import add_admin_to_db, delete_admin_from_db, get_admin_by_id
from app.keyboards import inline_admin_list, inline_single_cancel_button, main_actions_keyboard
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger


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
    return (username.startswith("@") and
            len(username) >= 5 and
            not username[1].isdigit() and
            username[1] != "_" and
            all(c.isalnum() or c == "_" for c in username[1:]))


@user.message(F.text == "👨🏻‍💻 Управление админами")
async def manage_admins(message: Message):
    logger.info("manage_admins_call")
    await message.answer(
        text="Выберите админа или создайте нового:",
        reply_markup=await inline_admin_list(
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
        )
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
            text="Некорректный формат! Используйте '@username' (минимум 5 символов, только буквы, цифры и _, "
                 "не начинается с цифры или _).\nВведите снова:",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback)
        )
        return
    success, response = await add_admin_to_db(username)
    if success:
        await message.answer(
            text=response,
            reply_markup=main_actions_keyboard
        )
        await state.clear()
    else:
        await message.answer(
            text=response,
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback)
        )
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)


@user.callback_query(F.data.startswith("admin_clicked"))
async def on_admin_clicked(callback: CallbackQuery):
    try:
        admin_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: админ не выбран!", show_alert=True)
        return
    admin = await get_admin_by_id(admin_id)
    if not admin:
        await callback.answer("Ошибка: админ не найден в базе данных!", show_alert=True)
        print(f"Ошибка: админ не найден с id {admin_id}!")
        return
    text = (
        f"Username админа: {admin.username}\n"
        "Админ имеет права на управление тегами (их добавление, изменение, архивацию и удаление)."
    )
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🗑️ Удалить админа",
                callback_data=f"{Callbacks.admin_delete_callback}:{admin_id}"
            )],
            [InlineKeyboardButton(
                text="↩ Вернуться назад",
                callback_data=Callbacks.return_to_admin_list_callback
            )]
        ]
    )
    await callback.message.edit_text(text=text, reply_markup=reply_markup)
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.admin_delete_callback))
async def on_admin_delete_callback(callback: CallbackQuery):
    try:
        admin_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: админ не выбран!", show_alert=True)
        return
    success, response = await delete_admin_from_db(admin_id)
    await callback.message.answer(
        text=response,
        reply_markup=main_actions_keyboard
    )
    await callback.message.delete()
    await callback.answer("")


@user.callback_query(F.data == Callbacks.return_to_admin_list_callback)
async def on_return_to_admin_list(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Выберите админа или создайте нового:",
        reply_markup=await inline_admin_list(
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
        )
    )
    await callback.answer("")
