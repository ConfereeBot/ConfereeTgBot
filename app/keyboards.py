from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import labels
from app.database.database import db
from app.roles.user.callbacks_enum import Callbacks

main_actions_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=labels.GET_RECORD), KeyboardButton(text=labels.RECORD)],
        [
            KeyboardButton(text=labels.MANAGE_TAGS),
            KeyboardButton(text=labels.MANAGE_ADMINS),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder=labels.CHOOSE_ACTION,
)

choose_recordings_search_method_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=labels.BY_TAG, callback_data=Callbacks.get_recording_by_tag_callback),
            InlineKeyboardButton(text=labels.BY_LINK, callback_data=Callbacks.get_recording_by_link_callback),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder=labels.CHOOSE_SEARCH_RECORD_TYPE,
)

async def inline_active_tag_list(
    on_item_clicked_callback: str,
    on_cancel_clicked_callback: str,
    on_archived_clicked_callback: str = None,
    on_item_create_clicked_callback: str = None,
) -> InlineKeyboardMarkup:
    tags = await db.get_active_tags()

    tags_list_keyboard = InlineKeyboardBuilder()
    for tag in tags:
        callback_data = f"{on_item_clicked_callback}:{str(tag.id)}"
        tags_list_keyboard.add(InlineKeyboardButton(text=tag.name, callback_data=callback_data))
    if on_item_create_clicked_callback is not None:
        tags_list_keyboard.add(
            InlineKeyboardButton(
                text=labels.CREATE_TAG, callback_data=on_item_create_clicked_callback
            )
        )
    if on_archived_clicked_callback is not None:
        tags_list_keyboard.add(
            InlineKeyboardButton(
                text=labels.ARCHIVED_TAGS,
                callback_data=on_archived_clicked_callback,
            )
        )
    tags_list_keyboard.add(
        InlineKeyboardButton(text=labels.CANCEL, callback_data=on_cancel_clicked_callback)
    )
    return tags_list_keyboard.adjust(1).as_markup()


tag_deletion_confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=labels.CANCEL_GET_BACK, callback_data=Callbacks.cancel_deletion
            )
        ],
        [
            InlineKeyboardButton(
                text=labels.ACCEPT_GET_BACK, callback_data=Callbacks.confirm_deletion
            )
        ],
    ]
)


async def inline_archived_tag_actions(
    on_unarchive_clicked_callback: str,
    on_delete_clicked_callback: str,
    on_back_clicked_callback: str,
) -> InlineKeyboardMarkup:
    print(f"unarchive_callback: {on_unarchive_clicked_callback}")  # Отладка
    print(f"delete_callback: {on_delete_clicked_callback}")  # Отладка
    print(f"back_callback: {on_back_clicked_callback}")  # Отладка
    tag_action_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.UNARCHIVE,
                    callback_data=on_unarchive_clicked_callback,
                )
            ],
            [InlineKeyboardButton(text=labels.REMOVE, callback_data=on_delete_clicked_callback)],
            [InlineKeyboardButton(text=labels.BACK, callback_data=on_back_clicked_callback)],
        ]
    )
    return tag_action_keyboard


async def inline_archived_tag_list(
    on_item_clicked_callback: str,
    on_back_clicked_callback: str,
) -> InlineKeyboardMarkup:
    tags = await db.get_archived_tags()

    tags_list_keyboard = InlineKeyboardBuilder()
    for tag in tags:
        callback_data = f"{on_item_clicked_callback}:{str(tag.id)}"
        tags_list_keyboard.add(InlineKeyboardButton(text=tag.name, callback_data=callback_data))
    tags_list_keyboard.add(
        InlineKeyboardButton(text=labels.BACK, callback_data=on_back_clicked_callback)
    )
    return tags_list_keyboard.adjust(1).as_markup()


async def inline_single_cancel_button(
    on_cancel_button_clicked_callback: str,
) -> InlineKeyboardMarkup:
    cancel_tag_enter_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.CANCEL, callback_data=on_cancel_button_clicked_callback
                )
            ]
        ]
    )

    return cancel_tag_enter_keyboard


async def inline_admin_list(on_cancel_clicked_callback: str) -> InlineKeyboardMarkup:
    admins = await db.get_all_admins()
    admin_list_keyboard = InlineKeyboardBuilder()
    for admin in admins:
        print(f"Admin data: {admin}")
        admin_list_keyboard.add(
            InlineKeyboardButton(text=admin.username, callback_data=f"admin_clicked:{admin.id}")
        )
    admin_list_keyboard.add(
        InlineKeyboardButton(text=labels.ADD_ADMIN, callback_data=Callbacks.add_admin_callback)
    )
    admin_list_keyboard.add(
        InlineKeyboardButton(text=labels.CANCEL, callback_data=on_cancel_clicked_callback)
    )
    return admin_list_keyboard.adjust(1).as_markup()


def manage_tag_inline_keyboard(tag_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.EDIT,
                    callback_data=f"{Callbacks.tag_edit_callback}:{tag_id}",
                ),
                InlineKeyboardButton(
                    text=labels.ARCHIVE,
                    callback_data=f"{Callbacks.tag_archive_callback}:{tag_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=labels.BACK, callback_data=Callbacks.cancel_tag_manage_callback
                )
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=labels.CHOOSE_ACTION,
    )
