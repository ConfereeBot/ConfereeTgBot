from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📥 Получить запись"), KeyboardButton(text="🎥 Записать")],
    [KeyboardButton(text="🗂️ Управление тегами"), KeyboardButton(text="👨🏻‍💻 Управление админами")],
],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)

choose_recordings_search_method_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🏷️ По тегу", url="https://ya.ru"),
     InlineKeyboardButton(text="🔗 По ссылке", url="https://ya.ru")],
],
    resize_keyboard=True,
    input_field_placeholder="Выберите способ поиска записи"
)

tag_list = ["Управление данными", "Архитектура ПК и ОС", "Правовая грамотность", "Python", "Java", "C++",
            "Компьютерные сети"]


async def inline_tag_list(on_item_clicked_callback: str, on_item_add_clicked_callback: str, on_cancel_clicked_callback: str) -> InlineKeyboardMarkup:
    tags_list_keyboard = InlineKeyboardBuilder()
    for tag in tag_list:
        tags_list_keyboard.add(InlineKeyboardButton(text=tag, callback_data=on_item_clicked_callback))
    tags_list_keyboard.add(InlineKeyboardButton(text="➕ Создать тег", callback_data=on_item_add_clicked_callback))
    tags_list_keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data=on_cancel_clicked_callback))
    return tags_list_keyboard.adjust(1).as_markup()

admin_list = ["@yuriy_magus", "@semyonq"]


async def inline_admin_list() -> InlineKeyboardMarkup:
    admin_list_keyboard = InlineKeyboardBuilder()
    for admin in admin_list:
        admin_list_keyboard.add(InlineKeyboardButton(text=admin, url="https://google.com"))
    admin_list_keyboard.add(InlineKeyboardButton(text="╋ Добавить админа", url="https://300.ya.ru"))
    admin_list_keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="on_cancel_primary_callback"))
    return admin_list_keyboard.adjust(1).as_markup()

manage_tag_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="on_tag_edit_callback"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data="on_tag_delete_callback")
    ],
    [InlineKeyboardButton(text="❌ Отмена", callback_data="on_cancel_tag_action_callback")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)
