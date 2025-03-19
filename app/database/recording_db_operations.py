from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import Optional

from app.database.database import db
from app.database.models.recording_DBO import Recording
from app.utils.logger import logger


async def add_recording_to_db(meeting_id: ObjectId, link: str) -> tuple[bool, str, Optional[ObjectId]]:
    """Добавляет новую запись в базу данных."""
    recording = Recording(conference_id=meeting_id, link=link)
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        await recordings_collection.insert_one(recording.model_dump(by_alias=True))
        logger.info(f"Запись с ссылкой '{link}' успешно добавлена с id: {recording.id}")
        return True, f"Запись с ссылкой '{link}' успешно добавлена!", recording.id
    except DuplicateKeyError:
        logger.warning(f"Запись с ссылкой '{link}' уже существует")
        return False, f"Запись с ссылкой '{link}' уже существует!", None
    except Exception as e:
        logger.error(f"Ошибка при добавлении записи '{link}': {e}")
        return False, f"Ошибка: {e}", None


async def get_recording_by_id(recording_id: str) -> Optional[Recording]:
    """Получает запись по её ID."""
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        recording_doc = await recordings_collection.find_one({"_id": ObjectId(recording_id)})
        if recording_doc:
            return Recording(**recording_doc)
        logger.warning(f"Запись с id '{recording_id}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении записи с id '{recording_id}': {e}")
        return None


async def get_recording_by_meeting_id(meeting_id: str) -> Optional[Recording]:
    """Получает запись по ID встречи."""
    recordings_collection: AgnosticCollection = db.db["recordings"]
    try:
        recording_doc = await recordings_collection.find_one({"meeting_id": ObjectId(meeting_id)})
        if recording_doc:
            return Recording(**recording_doc)
        logger.warning(f"Запись для встречи с id '{meeting_id}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении записи для встречи с id '{meeting_id}': {e}")
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
