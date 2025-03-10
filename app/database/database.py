from typing import List

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.config import MONGODB_URI, DB_NAME

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.database.models.tag_DBO import Tag
from app.roles.user.user_cmds import logger


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DB_NAME]

    async def ping(self):
        # check connection
        await self.db.command("ping")
        print("MongoDB connection successful")

    async def setup_indexes(self):
        await self.db["tags"].create_index("name", unique=True)
        print("Unique index on 'name' created for tags collection")

    async def get_active_tags(self) -> List[Tag]:
        tags_collection = self.db["tags"]
        tags = []
        async for tag_doc in tags_collection.find({"is_archived": False}):
            tags.append(Tag(**tag_doc))
        return tags

    async def get_archived_tags(self) -> List[Tag]:
        tags_collection = self.db["tags"]
        tags = []
        async for tag_doc in tags_collection.find({"is_archived": True}):
            tags.append(Tag(**tag_doc))
        return tags


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
    Deletes tag from DB by ID.
    Returns tuple (isSuccessful, message)
    """
    tags_collection: AgnosticCollection = db.db["tags"]
    try:
        result = await tags_collection.delete_one({"_id": ObjectId(tag_id)})
        if result.deleted_count == 0:
            logger.warning(f"Тег с id '{tag_id}' не найден")
            return False, f"Тег с id '{tag_id}' не найден!"
        logger.info(f"Тег с id '{tag_id}' успешно удалён")
        return True, f"Тег успешно удалён!"
    except Exception as e:
        logger.error(f"Ошибка при удалении тега с id '{tag_id}': {e}")
        return False, f"Ошибка: {e}"


db = Database()
