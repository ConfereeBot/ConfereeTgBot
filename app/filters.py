from aiogram.filters import Filter
from aiogram.types import Message

from app.config.roles import Role
from app.utils.is_owner import is_owner


class RoleFilter(Filter):
    """Фильтрация сообщений по роли.

    Args:
        role (Role): Роль.
    """

    def __init__(self, role: Role):
        self.role = role

    async def __call__(self, message: Message) -> bool:
        """Фильтрация роли.

        Args:
            message (Message): Объект сообщения.

        Returns:
            bool: Доступность для заданной роли.
        """

        if is_owner(str(message.from_user.id)) and self.role >= Role.ADMIN:
            return True

        return True
        # user = await get_user()
        # return user.role == self.role
