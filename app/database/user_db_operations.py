from typing import List, Optional

from app.config.roles import Role
from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.database.database import db
from app.database.models.user_DBO import User
from app.utils.logger import logger


async def add_user_if_not_exists(telegram_tag: str) -> tuple[bool, str, Optional[User]]:
    users_collection: AgnosticCollection = db.db["users"]
    try:
        existing_user = await users_collection.find_one({"telegram_tag": telegram_tag})
        if existing_user:
            logger.info(f"Пользователь '{telegram_tag}' уже существует в БД с id: {existing_user['_id']}")
            return True, f"Пользователь '{telegram_tag}' уже существует!", User(**existing_user)

        user = User(telegram_tag=telegram_tag, role=Role.USER)
        await users_collection.insert_one(user.model_dump(by_alias=True))
        logger.info(f"Новый пользователь '{telegram_tag}' добавлен с id: {user.id}")
        return True, f"Пользователь '{telegram_tag}' успешно добавлен!", user
    except DuplicateKeyError:
        logger.warning(f"Ошибка: дубликат telegram_tag '{telegram_tag}'")
        return False, f"Ошибка: пользователь '{telegram_tag}' уже существует!", None
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя '{telegram_tag}': {e}")
        return False, f"Ошибка: {e}", None


async def add_or_update_user_to_admin(telegram_tag: str) -> tuple[bool, str]:
    users_collection: AgnosticCollection = db.db["users"]
    try:
        existing_user = await users_collection.find_one({"telegram_tag": telegram_tag})
        if existing_user:
            if existing_user["role"] == Role.ADMIN:
                logger.warning(f"Пользователь '{telegram_tag}' уже является админом")
                return False, f"Пользователь '{telegram_tag}' уже является админом!"
            if existing_user["role"] == Role.OWNER:
                logger.warning(f"Пользователь '{telegram_tag}' является владельцем и не может быть изменён")
                return False, f"Пользователь '{telegram_tag}' является владельцем и не может быть изменён!"
            result = await users_collection.update_one(
                {"telegram_tag": telegram_tag},
                {"$set": {"role": Role.ADMIN}}
            )
            if result.modified_count > 0:
                logger.info(f"Пользователь '{telegram_tag}' повышен до админа")
                return True, f"Пользователь '{telegram_tag}' повышен до админа!"
            return False, f"Ошибка при обновлении роли пользователя '{telegram_tag}'!"
        else:
            user = User(telegram_tag=telegram_tag, role=Role.ADMIN)
            await users_collection.insert_one(user.model_dump(by_alias=True))
            logger.info(f"Новый админ '{telegram_tag}' добавлен с id: {user.id}")
            return True, f"Админ '{telegram_tag}' успешно добавлен!"
    except DuplicateKeyError:
        logger.warning(f"Ошибка: пользователь '{telegram_tag}' уже существует с другой ролью")
        return False, f"Ошибка: пользователь '{telegram_tag}' уже существует!"
    except Exception as e:
        logger.error(f"Ошибка при добавлении/обновлении админа '{telegram_tag}': {e}")
        return False, f"Ошибка: {e}"


async def get_all_users() -> List[User]:
    users_collection: AgnosticCollection = db.db["users"]
    users = []
    try:
        async for user_doc in users_collection.find():
            users.append(User(**user_doc))
        return users
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        return []


async def get_admins() -> List[User]:
    users_collection: AgnosticCollection = db.db["users"]
    admins = []
    try:
        async for user_doc in users_collection.find({"role": Role.ADMIN}):
            admins.append(User(**user_doc))
        return admins
    except Exception as e:
        logger.error(f"Ошибка при получении списка админов: {e}")
        return []


async def get_user_by_id(user_id: str) -> Optional[User]:
    users_collection: AgnosticCollection = db.db["users"]
    try:
        user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            return User(**user_doc)
        logger.warning(f"Пользователь с id '{user_id}' не найден")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя с id '{user_id}': {e}")
        return None


async def get_user_by_telegram_tag(telegram_tag: str) -> Optional[User]:
    users_collection: AgnosticCollection = db.db["users"]
    try:
        user_doc = await users_collection.find_one({"telegram_tag": telegram_tag})
        if user_doc:
            return User(**user_doc)
        logger.warning(f"Пользователь с тегом '{telegram_tag}' не найден")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя с тегом '{telegram_tag}': {e}")
        return None


async def demote_admin_to_user(user_id: str) -> tuple[bool, str]:
    users_collection: AgnosticCollection = db.db["users"]
    try:
        user = await get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь с id '{user_id}' не найден")
            return False, f"Пользователь с id '{user_id}' не найден!"
        if user.role != Role.ADMIN:
            logger.warning(f"Пользователь '{user.telegram_tag}' не является админом")
            return False, f"Пользователь '{user.telegram_tag}' не является админом!"
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"role": Role.USER}}
        )
        if result.modified_count == 0:
            logger.warning(f"Не удалось понизить роль пользователя с id '{user_id}'")
            return False, f"Не удалось понизить роль пользователя '{user.telegram_tag}'!"
        logger.info(f"Админ '{user.telegram_tag}' понижен до пользователя")
        return True, f"Админ '{user.telegram_tag}' понижен до пользователя!"
    except Exception as e:
        logger.error(f"Ошибка при понижении админа с id '{user_id}': {e}")
        return False, f"Ошибка: {e}"
