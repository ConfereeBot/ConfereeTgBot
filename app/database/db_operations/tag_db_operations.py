from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.database.db_operations.conference_db_operations import get_conferences_by_tag, delete_conference_by_id  # Импортируем
from app.database.database import db
from app.database.models.tag_DBO import Tag
from app.utils.logger import logger


async def add_tag_to_db(name: str) -> tuple[bool, str]:
    """
    Adds tag to DB.
    Returns tuple (isSuccessful, message)
    """
    tag = Tag(name=name)
    tags_collection: AgnosticCollection = db.db["tags"]

    try:
        await tags_collection.insert_one(tag.model_dump(by_alias=True))
        logger.info(f"Тег '{name}' успешно добавлен с id: {tag.id}")
        return True, f"Тег '{name}' успешно добавлен!"
    except DuplicateKeyError:
        logger.warning(f"Тег '{name}' уже существует")
        return False, (f"Тег '{name}' уже существует, \n"
                       f"выберите другое имя для тега.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении тега '{name}': {e}")
        return False, f"Ошибка: {e}"


async def update_tag_in_db(tag_id: str, new_name: str) -> tuple[bool, str]:
    """
    Updates tag name in DB by ID.
    Returns tuple (isSuccessful, message)
    """
    tags_collection: AgnosticCollection = db.db["tags"]
    try:
        result = await tags_collection.update_one(
            {"_id": ObjectId(tag_id)},
            {"$set": {"name": new_name}}
        )
        if result.matched_count == 0:
            logger.warning(f"Тег с id '{tag_id}' не найден")
            return False, f"Тег не найден!"
        if result.modified_count > 0:
            logger.info(f"Тег с id '{tag_id}' обновлён: новое имя '{new_name}'")
            return True, f"Тег успешно обновлён на '{new_name}'!"
        logger.warning(f"Тег с id '{tag_id}' не изменён (имя уже '{new_name}')")
        return True, f"Имя '{new_name}' уже установлено для тега."
    except DuplicateKeyError:
        logger.warning(f"Тег с именем '{new_name}' уже существует")
        return False, f"Тег с именем '{new_name}' уже существует, выберите другое имя."
    except Exception as e:
        logger.error(f"Ошибка при обновлении тега с id '{tag_id}': {e}")
        return False, f"Ошибка: {e}"


async def delete_tag_from_db(tag_id: str) -> tuple[bool, str]:
    """
    Deletes tag from DB by ID and its associated conferences.
    Returns tuple (isSuccessful, message)
    """
    tags_collection: AgnosticCollection = db.db["tags"]
    try:
        tag = await get_tag_by_id(tag_id)
        if not tag:
            logger.warning(f"Тег с id '{tag_id}' не найден")
            return False, f"Тег с id '{tag_id}' не найден!"

        conferences = await get_conferences_by_tag(tag_id)
        for conference in conferences:
            success, msg = await delete_conference_by_id(str(conference.id))
            if not success:
                logger.warning(f"Failed to delete conference {conference.id} for tag {tag_id}: {msg}")

        result = await tags_collection.delete_one({"_id": ObjectId(tag_id)})
        if result.deleted_count == 0:
            logger.warning(f"Тег с id '{tag_id}' не найден при удалении")
            return False, f"Тег с id '{tag_id}' не найден!"

        logger.info(f"Тег с id '{tag_id}' и связанные конференции успешно удалены")
        return True, f"Тег '{tag.name}' и все связанные конференции успешно удалены!"
    except Exception as e:
        logger.error(f"Ошибка при удалении тега с id '{tag_id}': {e}")
        return False, f"Ошибка: {e}"


async def unarchive_tag_in_db(tag_id: str) -> tuple[bool, str]:
    """
    Unarchives tag in DB by ID (sets is_archived to False).
    Returns tuple (isSuccessful, message)
    """
    tags_collection: AgnosticCollection = db.db["tags"]
    try:
        result = await tags_collection.update_one(
            {"_id": ObjectId(tag_id)},
            {"$set": {"is_archived": False}}
        )
        if result.matched_count == 0:
            logger.warning(f"Тег с id '{tag_id}' не найден")
            return False, f"Тег с id '{tag_id}' не найден!"
        if result.modified_count > 0:
            logger.info(f"Тег с id '{tag_id}' успешно разархивирован")
            return True, f"Тег успешно разархивирован!"
        logger.info(f"Тег с id '{tag_id}' уже был неархивированным")
        return True, f"Тег уже был неархивированным!"
    except Exception as e:
        logger.error(f"Ошибка при разархивировании тега с id '{tag_id}': {e}")
        return False, f"Ошибка: {e}"


async def archive_tag_in_db(tag_id: str) -> tuple[bool, str]:
    """
    Archives tag in DB by ID (sets is_archived to True).
    Returns tuple (isSuccessful, message)
    """
    tags_collection: AgnosticCollection = db.db["tags"]
    try:
        result = await tags_collection.update_one(
            {"_id": ObjectId(tag_id)},
            {"$set": {"is_archived": True}}
        )
        if result.matched_count == 0:
            logger.warning(f"Тег с id '{tag_id}' не найден")
            return False, f"Тег с id '{tag_id}' не найден!"
        if result.modified_count > 0:
            logger.info(f"Тег с id '{tag_id}' успешно архивирован")
            return True, f"Тег успешно архивирован!"
        logger.info(f"Тег с id '{tag_id}' уже был архивирован")
        return True, f"Тег уже был архивирован!"
    except Exception as e:
        logger.error(f"Ошибка при архивировании тега с id '{tag_id}': {e}")
        return False, f"Ошибка: {e}"


async def get_tag_by_id(tag_id: str) -> Tag | None:
    """
    Retrieves a tag from the DB by its ID.
    Returns Tag object or None if not found.
    """
    tags_collection: AgnosticCollection = db.db["tags"]
    try:
        tag_doc = await tags_collection.find_one({"_id": ObjectId(tag_id)})
        if tag_doc:
            return Tag(**tag_doc)
        logger.warning(f"Тег с id '{tag_id}' не найден")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении тега с id '{tag_id}': {e}")
        return None
