from aiogram import F, Router
from aiogram.types import Message

from app.config import labels
from app.config.roles import Role
from app.database.user_db_operations import get_user_by_telegram_tag
from app.filters import RoleFilter

admin = Router()
admin.message.filter(RoleFilter(Role.ADMIN))
admin.callback_query.filter(RoleFilter(Role.ADMIN))


@admin.message(F.text == labels.MANAGE_TAGS)
async def manage_tags(message: Message):
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    await message.answer(f"Управление тегами доступно для {user.role}! (Реализация в tags_management)")
