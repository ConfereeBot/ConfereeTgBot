from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

from app.config.roles import Role
from app.database.user_db_operations import get_user_by_telegram_tag
from app.utils.logger import logger


class RoleFilter(Filter):
    """Фильтрация сообщений и коллбэков по роли.

    Args:
        role (Role): Минимальная роль, необходимая для обработки.
    """

    def __init__(self, role: Role):
        self.role = role

    async def __call__(self, obj: Message | CallbackQuery) -> bool:
        """Фильтрация по роли пользователя.

        Args:
            obj (Message | CallbackQuery): Объект сообщения или коллбэка.

        Returns:
            bool: True, если роль пользователя >= требуемой роли, иначе False.
        """
        if isinstance(obj, Message):
            user = obj.from_user
        elif isinstance(obj, CallbackQuery):
            user = obj.from_user
        else:
            return False

        telegram_tag = f"@{user.username}" if user.username else f"@{user.id}"
        db_user = await get_user_by_telegram_tag(telegram_tag)
        if not db_user:
            logger.warning(f"Пользователь с тегом '{telegram_tag}' не найден в БД")
            return False

        # Преобразуем строку из базы в Role
        try:
            user_role = Role(db_user.role)
        except ValueError:
            logger.error(f"Некорректная роль '{db_user.role}' для пользователя '{telegram_tag}'")
            return False

        return user_role >= self.role
