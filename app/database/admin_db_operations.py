from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from app.database.database import db
from app.database.models.admin_DBO import Admin
from app.roles.user.user_cmds import logger


async def add_admin_to_db(username: str) -> tuple[bool, str]:
    admin = Admin(username=username)
    admins_collection: AgnosticCollection = db.db["admins"]
    try:
        await admins_collection.insert_one(admin.model_dump(by_alias=True))
        logger.info(f"Админ '{username}' успешно добавлен с id: {admin.id}")
        return True, f"Админ '{username}' успешно добавлен!"
    except DuplicateKeyError:
        logger.warning(f"Админ '{username}' уже существует")
        return False, f"Админ '{username}' уже существует! \n\nВведите другой тег для добавление нового админа:"
    except Exception as e:
        logger.error(f"Ошибка при добавлении админа '{username}': {e}")
        return False, f"Ошибка: {e}"


async def get_all_admins() -> list[Admin]:
    admins_collection: AgnosticCollection = db.db["admins"]
    admins = []
    try:
        async for admin_doc in admins_collection.find():
            admins.append(Admin(**admin_doc))
        return admins
    except Exception as e:
        logger.error(f"Ошибка при получении списка админов: {e}")
        return []


async def delete_admin_from_db(admin_id: str) -> tuple[bool, str]:
    admins_collection: AgnosticCollection = db.db["admins"]
    try:
        result = await admins_collection.delete_one({"_id": ObjectId(admin_id)})
        if result.deleted_count == 0:
            logger.warning(f"Админ с id '{admin_id}' не найден")
            return False, f"Админ с id '{admin_id}' не найден!"
        logger.info(f"Админ с id '{admin_id}' успешно удалён")
        return True, f"Админ успешно удалён!"
    except Exception as e:
        logger.error(f"Ошибка при удалении админа с id '{admin_id}': {e}")
        return False, f"Ошибка: {e}"


async def get_admin_by_id(admin_id: str) -> Admin | None:
    admins_collection: AgnosticCollection = db.db["admins"]
    try:
        print(f"Searching for admin with id: {admin_id}")  # Отладка
        admin_doc = await admins_collection.find_one({"_id": ObjectId(admin_id)})
        if admin_doc:
            print(f"Found admin: {admin_doc}")  # Отладка
            return Admin(**admin_doc)
        logger.warning(f"Админ с id '{admin_id}' не найден")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении админа с id '{admin_id}': {e}")
        return None
