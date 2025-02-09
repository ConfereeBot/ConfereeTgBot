from enum import StrEnum


class Role(StrEnum):
    """Класс IntEnum ролей пользователей."""

    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"

    def __lt__(self, other):
        roles = list(Role)
        return roles.index(self) < roles.index(other)

    def __le__(self, other):
        roles = list(Role)
        return roles.index(self) <= roles.index(other)

    def __gt__(self, other):
        roles = list(Role)
        return roles.index(self) > roles.index(other)

    def __ge__(self, other):
        roles = list(Role)
        return roles.index(self) >= roles.index(other)
