from typing import List, Optional

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.bot import bot
from app.config.config import OWNERS
from app.config.roles import Role
from app.database.database import db
from app.database.models.user_DBO import User
from app.keyboards import main_actions_keyboard
from app.utils.logger import logger


async def add_user_if_not_exists(telegram_tag: str, telegram_id: int | None) -> tuple[bool, str, User | None]:
    """Добавляет нового пользователя в БД."""
    user_data = {
        "telegram_tag": telegram_tag,
        "telegram_id": telegram_id,
        "role": Role.USER
    }
    result = await db.db.users.insert_one(user_data)
    if result.inserted_id:
        user = User(_id=result.inserted_id, telegram_tag=telegram_tag, telegram_id=telegram_id, role=Role.USER)
        return True, f"Пользователь {telegram_tag} успешно добавлен с ролью {Role.USER}", user
    return False, "Ошибка при добавлении пользователя", None


async def get_user_by_telegram_tag(telegram_tag: str) -> User | None:
    """Получает пользователя по telegram_tag."""
    user_data = await db.db.users.find_one({"telegram_tag": telegram_tag})
    if user_data:
        return User(**user_data)
    return None


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Получает пользователя по telegram_id."""
    user_data = await db.db.users.find_one({"telegram_id": telegram_id})
    if user_data:
        return User(**user_data)
    return None


async def update_user_telegram_tag(user_id: ObjectId, new_telegram_tag: str) -> bool:
    """Обновляет telegram_tag пользователя."""
        
    result = await db.db.users.update_one(
        {"_id": user_id},
        {"$set": {"telegram_tag": new_telegram_tag}}
    )
    return result.modified_count > 0


async def update_user_telegram_id(user_id: ObjectId, telegram_id: int) -> bool:
    """Обновляет telegram_id пользователя."""
    result = await db.db.users.update_one(
        {"_id": user_id},
        {"$set": {"telegram_id": telegram_id}}
    )
    return result.modified_count > 0


async def add_or_update_user_to_admin(telegram_tag: str) -> tuple[bool, str]:
    """Добавляет нового пользователя с ролью admin или обновляет существующего до admin."""
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
                notify_successful = await notify_user_about_upgrade_to_admin(telegram_tag)
                if not notify_successful:
                    logger.info(f"Не удалось оповестить пользователя '{telegram_tag}' о повышении.")
                else:
                    logger.info(f"Оповещение пользователю '{telegram_tag}' о повышении отправлено.")
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
    """Получает всех пользователей."""
    users_collection: AgnosticCollection = db.db["users"]
    users = []
    try:
        async for user_doc in users_collection.find():
            users.append(User(**user_doc))
        return users
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        return []


async def notify_user_about_upgrade_to_admin(telegram_tag: str) -> bool:
    user = await get_user_by_telegram_tag(telegram_tag)
    if user and user.telegram_id is not None:
        await bot.send_message(
            chat_id=user.telegram_id,
            text="📢 Внимание!\n\nВы были повышены до админа администратором!",
            reply_markup=main_actions_keyboard(Role.ADMIN)
        )
        return True
    return False


async def notify_user_about_downgrade_to_user(telegram_tag) -> bool:
    user = await get_user_by_telegram_tag(telegram_tag)
    if user and user.telegram_id is not None:
        await bot.send_message(
            chat_id=user.telegram_id,
            text="📢 Внимание!\n\nВы были понижены до обычного пользователя администратором.",
            reply_markup=main_actions_keyboard(Role.USER)
        )
        return True
    return False


async def get_admins() -> List[User]:
    """Получает всех пользователей с ролью admin."""
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
    """Получает пользователя по ID."""
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


async def demote_admin_to_user(user_id: str) -> tuple[bool, str]:
    """Понижает админа до роли user."""
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
        notify_successful = await notify_user_about_downgrade_to_user(user.telegram_tag)
        if not notify_successful:
            logger.info(f"Не удалось оповестить пользователя '{user.telegram_tag}' о понижении")
        else:
            logger.info(f"Оповещение пользователя '{user.telegram_tag}' о понижении отправлено!")
        logger.info(f"Админ '{user.telegram_tag}' понижен до пользователя")
        return True, f"Админ '{user.telegram_tag}' понижен до пользователя!"
    except Exception as e:
        logger.error(f"Ошибка при понижении админа с id '{user_id}': {e}")
        return False, f"Ошибка: {e}"


async def ensure_owner_role(telegram_tag: str, telegram_id: int | None = None) -> tuple[bool, str]:
    """Устанавливает роль OWNER для пользователя, если он в OWNERS."""
    user = await get_user_by_telegram_id(telegram_id) if telegram_id else None
    if not user:
        user = await get_user_by_telegram_tag(telegram_tag)

    if not user:
        success, response, new_user = await add_user_if_not_exists(telegram_tag, telegram_id)
        if not success:
            return False, response
        user = new_user

    if telegram_tag in OWNERS and user.role != Role.OWNER:
        await db.db.users.update_one(
            {"_id": user.id},
            {"$set": {"role": Role.OWNER}}
        )
        return True, f"Роль пользователя {telegram_tag} обновлена до OWNER"
    return True, f"Пользователь {telegram_tag} уже имеет роль {user.role}"


async def delete_user_by_telegram_tag_with_no_telegram_id(telegram_tag: str) -> tuple[bool, str]:
    try:
        result = await db.db.users.delete_one({
            "telegram_tag": telegram_tag,
            "telegram_id": {"$eq": None}
        })

        if result.deleted_count > 0:
            logger.info(f"Пользователь с тегом '{telegram_tag}' успешно удалён")
            return True, f"Пользователь '{telegram_tag}' успешно удалён из базы данных."
        else:
            logger.info(f"Пользователь с тегом '{telegram_tag}' не найден для удаления")
            return False, f"Пользователь '{telegram_tag}' не найден в базе данных."

    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя с тегом '{telegram_tag}': {e}")
        return False, f"Ошибка при удалении пользователя: {str(e)}"


async def handle_user_on_start(telegram_tag: str, telegram_id: int) -> User:
    """Обрабатывает пользователя при вызове /start."""
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        print("User found with this telegram id")
        if user.telegram_tag != telegram_tag:
            logger.info(f"Обновляем telegram_tag для {telegram_id}: {user.telegram_tag} -> {telegram_tag}")
            await delete_user_by_telegram_tag_with_no_telegram_id(user.telegram_tag)
            await update_user_telegram_tag(user.id, telegram_tag)
            user.telegram_tag = telegram_tag
        return user

    user = await get_user_by_telegram_tag(telegram_tag)
    if user:
        if user.telegram_id is None or user.telegram_id != telegram_id:
            logger.info(f"Обновляем telegram_id для {telegram_tag}: {user.telegram_id} -> {telegram_id}")
            await update_user_telegram_id(user.id, telegram_id)
            user.telegram_id = telegram_id
        return user

    success, response, user = await add_user_if_not_exists(telegram_tag, telegram_id)
    if not success:
        raise Exception(response)
    logger.info(response)
    return user
