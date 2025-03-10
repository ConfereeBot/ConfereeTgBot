from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.database import db
from app.roles.user.callbacks_enum import Callbacks

main_actions_keyboard = ReplyKeyboardMarkup(keyboard=[
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


async def inline_tag_list(
        on_item_clicked_callback: str,
        on_cancel_clicked_callback: str,
        on_item_create_clicked_callback: str = None
) -> InlineKeyboardMarkup:
    print(f"inline_tag_list got on_item_clicked_callback={on_item_create_clicked_callback}")
    tags = await db.get_all_tags()

    tags_list_keyboard = InlineKeyboardBuilder()
    for tag in tags:
        callback_data = f"{on_item_clicked_callback}:{str(tag.id)}"
        tags_list_keyboard.add(InlineKeyboardButton(
            text=tag.name,
            callback_data=callback_data
        ))
    if on_item_create_clicked_callback is not None:
        tags_list_keyboard.add(InlineKeyboardButton(
            text="➕ Создать тег",
            callback_data=on_item_create_clicked_callback
        ))
    tags_list_keyboard.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=on_cancel_clicked_callback
    ))
    return tags_list_keyboard.adjust(1).as_markup()


async def inline_single_cancel_button(
        on_cancel_button_clicked_callback: str
) -> InlineKeyboardMarkup:
    cancel_tag_enter_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=on_cancel_button_clicked_callback
            )]
        ]
    )

    return cancel_tag_enter_keyboard


admin_list = ["@yuriy_magus", "@semyonq"]


async def inline_admin_list() -> InlineKeyboardMarkup:
    admin_list_keyboard = InlineKeyboardBuilder()
    for admin in admin_list:
        admin_list_keyboard.add(InlineKeyboardButton(text=admin, url="https://google.com"))
    admin_list_keyboard.add(InlineKeyboardButton(text="➕ Добавить админа", url="https://300.ya.ru"))
    admin_list_keyboard.add(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=Callbacks.cancel_primary_action_callback
        )
    )
    return admin_list_keyboard.adjust(1).as_markup()


def manage_tag_inline_keyboard(tag_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"{Callbacks.tag_edit_callback}:{tag_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=f"{Callbacks.tag_delete_callback}:{tag_id}"
                )
            ],
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=Callbacks.cancel_tag_manage_callback
            )]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
