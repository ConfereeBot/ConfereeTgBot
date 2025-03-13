from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import List, Optional

from app.database.database import db
from app.database.models.conference_DBO import Conference
from app.database.models.tag_DBO import Tag
from app.roles.user.user_cmds import logger


async def add_conference_to_db(link: str, tag: Tag) -> tuple[bool, str, Optional[ObjectId]]:
    """Add a new conference to the database.

    Args:
        link (str): The Google Meet conference link.
        tag (Tag): The tag associated with the conference.

    Returns:
        tuple[bool, str, Optional[ObjectId]]: A tuple containing:
            - Success flag (True if added, False if failed).
            - Response message.
            - Conference ID (or None if failed).
    """
    conference = Conference(link=link, tag=tag)
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        await conferences_collection.insert_one(conference.model_dump(by_alias=True))
        logger.info(f"Conference with link '{link}' successfully added with id: {conference.id}")
        return True, f"Conference with link '{link}' successfully added!", conference.id
    except DuplicateKeyError:
        logger.warning(f"Conference with link '{link}' already exists")
        return False, f"Conference with link '{link}' already exists!", None
    except Exception as e:
        logger.error(f"Error adding conference '{link}': {e}")
        return False, f"Error: {e}", None


async def get_conference_by_id(conference_id: str) -> Optional[Conference]:
    """Retrieve a conference by its ID.

    Args:
        conference_id (str): The ID of the conference to retrieve.

    Returns:
        Optional[Conference]: The conference object if found, None otherwise.
    """
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference_doc = await conferences_collection.find_one({"_id": ObjectId(conference_id)})
        if conference_doc:
            tag = Tag(**conference_doc["tag"])
            conference_doc.pop("tag")
            return Conference(**conference_doc, tag=tag)
        logger.warning(f"Conference with id '{conference_id}' not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving conference with id '{conference_id}': {e}")
        return None


async def get_conferences_by_tag(tag_id: str) -> List[Conference]:
    """Retrieve all conferences associated with a specific tag.

    Args:
        tag_id (str): The ID of the tag to filter conferences by.

    Returns:
        List[Conference]: A list of conference objects matching the tag.
    """
    conferences_collection: AgnosticCollection = db.db["conferences"]
    conferences = []
    try:
        async for conference_doc in conferences_collection.find({"tag._id": ObjectId(tag_id)}):
            tag = Tag(**conference_doc["tag"])
            conference_doc.pop("tag")
            conferences.append(Conference(**conference_doc, tag=tag))
        return conferences
    except Exception as e:
        logger.error(f"Error retrieving conferences by tag '{tag_id}': {e}")
        return []


async def get_conference_by_link(link: str) -> Optional[Conference]:
    """Retrieve a conference by its link.

    Args:
        link (str): The Google Meet link of the conference to retrieve.

    Returns:
        Optional[Conference]: The conference object if found, None otherwise.
    """
    conferences_collection: AgnosticCollection = db.db["conferences"]
    try:
        conference_doc = await conferences_collection.find_one({"link": link})
        if conference_doc:
            tag = Tag(**conference_doc["tag"])
            conference_doc.pop("tag")
            return Conference(**conference_doc, tag=tag)
        logger.warning(f"Conference with link '{link}' not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving conference with link '{link}': {e}")
        return None


async def add_recording_to_conference(conference_id: str, recording_id: ObjectId) -> tuple[bool, str]:
    """Add a recording ID to the recordings array of a conference.

    Args:
        conference_id (str): The ID of the conference to update.
        recording_id (ObjectId): The ID of the recording to add.

    Returns:
        tuple[bool, str]: A tuple containing:
            - Success flag (True if updated, False if failed).
            - Response message.
    """
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
