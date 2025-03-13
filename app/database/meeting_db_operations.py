from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import List, Optional

from app.database.database import db
from app.database.models.meeting_DBO import Meeting
from app.database.models.tag_DBO import Tag
from app.roles.user.user_cmds import logger


async def add_meeting_to_db(link: str, tag: Tag) -> tuple[bool, str]:
    """Добавляет новую встречу в базу данных."""
    meeting = Meeting(link=link, tag=tag)
    meetings_collection: AgnosticCollection = db.db["meetings"]
    try:
        await meetings_collection.insert_one(meeting.model_dump(by_alias=True))
        logger.info(f"Встреча с ссылкой '{link}' успешно добавлена с id: {meeting.id}")
        return True, f"Встреча с ссылкой '{link}' успешно добавлена!"
    except DuplicateKeyError:
        logger.warning(f"Встреча с ссылкой '{link}' уже существует")
        return False, f"Встреча с ссылкой '{link}' уже существует!"
    except Exception as e:
        logger.error(f"Ошибка при добавлении встречи '{link}': {e}")
        return False, f"Ошибка: {e}"


async def get_meeting_by_id(meeting_id: str) -> Optional[Meeting]:
    """Получает встречу по её ID."""
    meetings_collection: AgnosticCollection = db.db["meetings"]
    try:
        meeting_doc = await meetings_collection.find_one({"_id": ObjectId(meeting_id)})
        if meeting_doc:
            tag = Tag(**meeting_doc["tag"])
            return Meeting(**meeting_doc, tag=tag)
        logger.warning(f"Встреча с id '{meeting_id}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении встречи с id '{meeting_id}': {e}")
        return None


async def get_meetings_by_tag(tag_id: str) -> List[Meeting]:
    """Получает все встречи, связанные с определённым тегом."""
    meetings_collection: AgnosticCollection = db.db["meetings"]
    meetings = []
    try:
        async for meeting_doc in meetings_collection.find({"tag._id": ObjectId(tag_id)}):
            tag = Tag(**meeting_doc["tag"])
            meetings.append(Meeting(**meeting_doc, tag=tag))
        return meetings
    except Exception as e:
        logger.error(f"Ошибка при получении встреч по тегу '{tag_id}': {e}")
        return []


async def get_meeting_by_link(link: str) -> Optional[Meeting]:
    """Получает встречу по ссылке."""
    meetings_collection: AgnosticCollection = db.db["meetings"]
    try:
        meeting_doc = await meetings_collection.find_one({"link": link})
        if meeting_doc:
            tag = Tag(**meeting_doc["tag"])
            return Meeting(**meeting_doc, tag=tag)
        logger.warning(f"Встреча с ссылкой '{link}' не найдена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении встречи с ссылкой '{link}': {e}")
        return None


async def update_meeting_recording(meeting_id: str, recording_id: ObjectId) -> tuple[bool, str]:
    """Обновляет встречу, добавляя ID записи."""
    meetings_collection: AgnosticCollection = db.db["meetings"]
    try:
        result = await meetings_collection.update_one(
            {"_id": ObjectId(meeting_id)},
            {"$set": {"recording": recording_id}}
        )
        if result.modified_count == 0:
            logger.warning(f"Встреча с id '{meeting_id}' не найдена или запись уже установлена")
            return False, f"Встреча с id '{meeting_id}' не найдена или запись уже установлена!"
        logger.info(f"Встреча с id '{meeting_id}' обновлена с записью {recording_id}")
        return True, f"Встреча успешно обновлена с записью!"
    except Exception as e:
        logger.error(f"Ошибка при обновлении встречи с id '{meeting_id}': {e}")
        return False, f"Ошибка: {e}"
