from bson import ObjectId

from app.config.config import OWNERS
from app.config.roles import Role
from app.database.database import db
from app.database.models.user_DBO import User
from app.utils.logger import logger


async def add_user_if_not_exists(telegram_tag: str, telegram_id: int) -> tuple[bool, str, User | None]:
    """Добавляет нового пользователя в БД."""
    user_data = {
        "telegram_tag": telegram_tag,
        "telegram_id": telegram_id,
        "role": Role.USER
    }
    result = await db.users.insert_one(user_data)
    if result.inserted_id:
        user = User(_id=result.inserted_id, telegram_tag=telegram_tag, telegram_id=telegram_id, role=Role.USER)
        return True, f"Пользователь {telegram_tag} успешно добавлен с ролью {Role.USER}", user
    return False, "Ошибка при добавлении пользователя", None


async def get_user_by_telegram_tag(telegram_tag: str) -> User | None:
    """Получает пользователя по telegram_tag."""
    user_data = await db.users.find_one({"telegram_tag": telegram_tag})
    if user_data:
        return User(**user_data)
    return None


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Получает пользователя по telegram_id."""
    user_data = await db.users.find_one({"telegram_id": telegram_id})
    if user_data:
        return User(**user_data)
    return None


async def update_user_telegram_tag(user_id: ObjectId, new_telegram_tag: str) -> bool:
    """Обновляет telegram_tag пользователя."""
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"telegram_tag": new_telegram_tag}}
    )
    return result.modified_count > 0


async def update_user_telegram_id(user_id: ObjectId, telegram_id: int) -> bool:
    """Обновляет telegram_id пользователя."""
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"telegram_id": telegram_id}}
    )
    return result.modified_count > 0


async def ensure_owner_role(telegram_tag: str, telegram_id: int | None = None) -> tuple[bool, str]:
    """Устанавливает роль OWNER для пользователя, если он в OWNERS."""
    user = await get_user_by_telegram_id(telegram_id) if telegram_id else None
    if not user:
        user = await get_user_by_telegram_tag(telegram_tag)

    if not user:
        success, response, new_user = await add_user_if_not_exists(telegram_tag, telegram_id or 0)
        if not success:
            return False, response
        user = new_user

    if telegram_tag in OWNERS and user.role != Role.OWNER:
        await db.users.update_one(
            {"_id": user.id},
            {"$set": {"role": Role.OWNER}}
        )
        return True, f"Роль пользователя {telegram_tag} обновлена до OWNER"
    return True, f"Пользователь {telegram_tag} уже имеет роль {user.role}"


async def handle_user_on_start(telegram_tag: str, telegram_id: int) -> User:
    """Обрабатывает пользователя при вызове /start."""
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        if user.telegram_tag != telegram_tag:
            logger.info(f"Обновляем telegram_tag для {telegram_id}: {user.telegram_tag} -> {telegram_tag}")
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
