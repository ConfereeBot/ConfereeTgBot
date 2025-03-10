from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.keyboards import inline_tag_list, manage_tag_inline_keyboard
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import user, logger


async def manage_tags(event: Message | CallbackQuery, state: FSMContext = None):
    logger.info("manage_tags_call")
    if state:
        await state.clear()
    text = "Выберите тег или создайте новый:"
    reply_markup = await inline_tag_list(
        on_item_clicked_callback=Callbacks.tag_clicked_manage_callback,
        on_item_create_clicked_callback=Callbacks.tag_create_callback,
        on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback
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


@user.callback_query(F.data.startswith(Callbacks.tag_clicked_manage_callback))
async def tag_clicked_manage_callback(callback: CallbackQuery):
    print("tag_clicked_manage_callback started")
    try:
        tag_id = callback.data.split(":")[1]  # Извлекаем tag_id
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите, что вы хотите сделать с тегом",
        reply_markup=manage_tag_inline_keyboard(tag_id)
    )
