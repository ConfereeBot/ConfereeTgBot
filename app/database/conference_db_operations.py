from typing import List, Optional

from bson import ObjectId
from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError

from app.database.database import db
from app.database.models.conference_DBO import Conference
from app.database.recording_db_operations import delete_recording_from_db  # Импортируем для каскадного удаления
from app.roles.user.user_cmds import logger


async def conference_exists_by_link(meet_link: str) -> bool:
    """Check if a conference with the given link already exists in the database."""
    existing_conference = await db.db.conferences.find_one({"link": meet_link})
    return bool(existing_conference)


async def add_conference_to_db(
        meet_link: str,
        tag_id: ObjectId,
        timestamp: int,
        timezone: int,
        periodicity: Optional[int] = None
) -> tuple[bool, str]:
    """
    Adds a new conference to the database.

    Returns:
        tuple[bool, str]: A tuple containing:
            - Success flag (True if inserted, False if failed).
            - Response message.
    """
    conference = {
        "link": meet_link,
        "tag_id": tag_id,
        "timestamp": timestamp,
        "timezone": timezone,
        "periodicity": periodicity,
        "recordings": []
    }
    try:
        result = await db.db.conferences.insert_one(conference)
        return True, f"Конференция с ссылкой {meet_link} успешно добавлена!"
    except DuplicateKeyError:
        return False, f"Конференция с ссылкой '{meet_link}' уже существует!"


async def get_conference_by_id(conference_id: str) -> Optional[Conference]:
    """Retrieve a conference by its ID."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference_doc = await conferences_collection.find_one({"_id": ObjectId(conference_id)})
        if conference_doc:
            return Conference(**conference_doc)
        logger.warning(f"Conference with id '{conference_id}' not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving conference with id '{conference_id}': {e}")
        return None


async def get_conferences_by_tag(tag_id: str) -> List[Conference]:
    """Retrieve all conferences associated with a specific tag."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    conferences = []
    try:
        async for conference_doc in conferences_collection.find({"tag_id": ObjectId(tag_id)}):
            conferences.append(Conference(**conference_doc))
        return conferences
    except Exception as e:
        logger.error(f"Error retrieving conferences by tag '{tag_id}': {e}")
        return []


async def get_conference_by_link(link: str) -> Optional[Conference]:
    """Retrieve a conference by its link."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference_doc = await conferences_collection.find_one({"link": link})
        if conference_doc:
            return Conference(**conference_doc)
        logger.warning(f"Conference with link '{link}' not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving conference with link '{link}': {e}")
        return None


async def add_recording_to_conference(conference_id: str, recording_id: ObjectId) -> tuple[bool, str]:
    """Add a recording ID to the recordings array of a conference."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        result = await conferences_collection.update_one(
            {"_id": ObjectId(conference_id)},
            {"$push": {"recordings": recording_id}}
        )
        if result.modified_count == 0:
            logger.warning(f"Conference with id '{conference_id}' not found")
            return False, f"Conference with id '{conference_id}' not found!"
        logger.info(f"Recording {recording_id} added to conference with id '{conference_id}'")
        return True, f"Recording successfully added to conference!"
    except Exception as e:
        logger.error(f"Error updating conference with id '{conference_id}': {e}")
        return False, f"Error: {e}"


async def delete_conference_by_id(conference_id: str) -> tuple[bool, str]:
    """Delete a conference by its ID from the database and its associated recordings."""
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference = await get_conference_by_id(conference_id)
        if not conference:
            logger.warning(f"Conference with id '{conference_id}' not found for deletion")
            return False, f"Конференция с ID '{conference_id}' не найдена!"

        for recording_id in conference.recordings:
            success, msg = await delete_recording_from_db(str(recording_id))
            if not success:
                logger.warning(f"Failed to delete recording {recording_id} for conference {conference_id}: {msg}")

        result = await conferences_collection.delete_one({"_id": ObjectId(conference_id)})
        if result.deleted_count == 0:
            logger.warning(f"Conference with id '{conference_id}' not found during deletion")
            return False, f"Конференция с ссылкой '{conference.link}' не найдена!"

        logger.info(f"Conference with id '{conference_id}' and its recordings deleted successfully")
        return True, f"Конференция с ссылкой '{conference.link}' и все связанные записи успешно удалены!"
    except Exception as e:
        logger.error(f"Error deleting conference with id '{conference_id}': {e}")
        return False, f"Ошибка при удалении конференции: {e}"
