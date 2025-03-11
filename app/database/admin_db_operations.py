from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.database.database import db
from app.database.models.admin_DBO import Admin
from app.roles.user.user_cmds import logger


async def add_admin_to_db(username: str) -> tuple[bool, str]:
    """
    Adds admin to DB.
    Returns tuple (isSuccessful, message)
    """
    admin = Admin(username=username)
    admins_collection: AgnosticCollection = db.db["admins"]
    try:
        await admins_collection.insert_one(admin.model_dump(by_alias=True))
        logger.info(f"Админ '{username}' успешно добавлен с id: {admin.id}")
        return True, f"Админ '{username}' успешно добавлен!"
    except DuplicateKeyError:
        logger.warning(f"Админ '{username}' уже существует")
        return False, f"Админ '{username}' уже существует!"
    except Exception as e:
        logger.error(f"Ошибка при добавлении админа '{username}': {e}")
        return False, f"Ошибка: {e}"


async def get_all_admins() -> list[Admin]:
    """
    Retrieves all admins from the DB.
    Returns list of Admin objects.
    """
    admins_collection: AgnosticCollection = db.db["admins"]
    admins = []
    try:
        async for admin_doc in admins_collection.find():
            admins.append(Admin(**admin_doc))
        return admins
    except Exception as e:
        logger.error(f"Ошибка при получении списка админов: {e}")
        return []
