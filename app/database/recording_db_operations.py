from typing import List, Optional

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.database.database import db
from app.database.models.recording_DBO import Recording
from app.database.models.tag_DBO import Tag
from app.roles.user.user_cmds import logger


async def add_recording_to_db(link: str, tag: Tag) -> tuple[bool, str]:
    """Добавляет новую запись в базу данных."""
    recording = Recording(link=link, tag=tag)
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        await recordings_collection.insert_one(recording.model_dump(by_alias=True))
        logger.info(f"Запись с ссылкой '{link}' успешно добавлена с id: {recording.id}")
        return True, f"Запись с ссылкой '{link}' успешно добавлена!"
    except DuplicateKeyError:
        logger.warning(f"Запись с ссылкой '{link}' уже существует")
        return False, f"Запись с ссылкой '{link}' уже существует!"
    except Exception as e:
        logger.error(f"Ошибка при добавлении записи '{link}': {e}")
        return False, f"Ошибка: {e}"


async def get_recording_by_id(recording_id: str) -> Optional[Recording]:
    """Получает запись по её ID."""
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        recording_doc = await recordings_collection.find_one({"_id": ObjectId(recording_id)})
        if recording_doc:
            tag = Tag(**recording_doc["tag"])  # Tag обязателен, так что всегда будет
            return Recording(**recording_doc, tag=tag)
        logger.warning(f"Запись с id '{recording_id}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении записи с id '{recording_id}': {e}")
        return None


async def get_recordings_by_tag(tag_id: str) -> List[Recording]:
    """Получает все записи, связанные с определённым тегом."""
    recordings_collection: AgnosticCollection = db.db["recordings"]
    recordings = []
    try:
        async for recording_doc in recordings_collection.find({"tag._id": ObjectId(tag_id)}):
            tag = Tag(**recording_doc["tag"])  # Tag обязателен
            recordings.append(Recording(**recording_doc, tag=tag))
        return recordings
    except Exception as e:
        logger.error(f"Ошибка при получении записей по тегу '{tag_id}': {e}")
        return []


async def get_recording_by_link(link: str) -> Optional[Recording]:
    """Получает запись по ссылке."""
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        recording_doc = await recordings_collection.find_one({"link": link})
        if recording_doc:
            tag = Tag(**recording_doc["tag"])  # Tag обязателен
            return Recording(**recording_doc, tag=tag)
        logger.warning(f"Запись с ссылкой '{link}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении записи с ссылкой '{link}': {e}")
        return None


async def delete_recording_from_db(recording_id: str) -> tuple[bool, str]:
    """Удаляет запись по её ID."""
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        result = await recordings_collection.delete_one({"_id": ObjectId(recording_id)})
        if result.deleted_count == 0:
            logger.warning(f"Запись с id '{recording_id}' не найдена")
            return False, f"Запись с id '{recording_id}' не найдена!"
        logger.info(f"Запись с id '{recording_id}' успешно удалена")
        return True, f"Запись успешно удалена!"
    except Exception as e:
        logger.error(f"Ошибка при удалении записи с id '{recording_id}': {e}")
        return False, f"Ошибка: {e}"
