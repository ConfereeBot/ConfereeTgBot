from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import List, Optional

from app.database.database import db
from app.database.models.conference_DBO import Conference
from app.database.models.tag_DBO import Tag
from app.roles.user.user_cmds import logger


async def add_conference_to_db(link: str, tag: Tag) -> tuple[bool, str, Optional[ObjectId]]:
    """Inserts new conference into db."""
    conference = Conference(link=link, tag=tag)
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        await conferences_collection.insert_one(conference.model_dump(by_alias=True))
        logger.info(f"Конференция с ссылкой '{link}' успешно добавлена с id: {conference.id}")
        return True, f"Конференция с ссылкой '{link}' успешно добавлена!", conference.id
    except DuplicateKeyError:
        logger.warning(f"Конференция с ссылкой '{link}' уже существует")
        return False, f"Конференция с ссылкой '{link}' уже существует!", None
    except Exception as e:
        logger.error(f"Ошибка при добавлении конференции '{link}': {e}")
        return False, f"Ошибка: {e}", None


async def get_conference_by_id(conference_id: str) -> Optional[Conference]:
    """Finds conference by its ID."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference_doc = await conferences_collection.find_one({"_id": ObjectId(conference_id)})
        if conference_doc:
            tag = Tag(**conference_doc["tag"])
            return Conference(**conference_doc, tag=tag)
        logger.warning(f"Конференция с id '{conference_id}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении конференции с id '{conference_id}': {e}")
        return None


async def get_conferences_by_tag(tag_id: str) -> List[Conference]:
    """Finds all conference with the given tag id."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    conferences = []
    try:
        async for conference_doc in conferences_collection.find({"tag._id": ObjectId(tag_id)}):
            tag = Tag(**conference_doc["tag"])
            conferences.append(Conference(**conference_doc, tag=tag))
        return conferences
    except Exception as e:
        logger.error(f"Ошибка при получении конференций по тегу '{tag_id}': {e}")
        return []


async def get_conference_by_link(link: str) -> Optional[Conference]:
    """Finds conference by link."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference_doc = await conferences_collection.find_one({"link": link})
        if conference_doc:
            tag = Tag(**conference_doc["tag"])
            return Conference(**conference_doc, tag=tag)
        logger.warning(f"Конференция с ссылкой '{link}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении конференции с ссылкой '{link}': {e}")
        return None


async def add_recording_to_conference(conference_id: str, recording_id: ObjectId) -> tuple[bool, str]:
    """Adds recording's ID into recordings array of conference."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        result = await conferences_collection.update_one(
            {"_id": ObjectId(conference_id)},
            {"$push": {"recordings": recording_id}}
        )
        if result.modified_count == 0:
            logger.warning(f"Конференция с id '{conference_id}' не найдена")
            return False, f"Конференция с id '{conference_id}' не найдена!"
        logger.info(f"Запись {recording_id} добавлена в конференцию с id '{conference_id}'")
        return True, f"Запись успешно добавлена в конференцию!"
    except Exception as e:
        logger.error(f"Ошибка при обновлении конференции с id '{conference_id}': {e}")
        return False, f"Ошибка: {e}"
