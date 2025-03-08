from motor.core import AgnosticCollection
from pymongo.errors import DuplicateKeyError
from app.database.database import db
from app.database.models.tag_DBO import Tag
import logging

logger = logging.getLogger(__name__)


async def add_tag(name: str) -> tuple[bool, str]:
    """
    Inserts tag into DB.
    Returns tuple (isSuccessful, message).
    """
    tag = Tag(name=name)
    tags_collection: AgnosticCollection = db.db["tags"]

    try:
        await tags_collection.insert_one(tag.model_dump(by_alias=True))
        logger.info(f"Тег '{name}' успешно добавлен с id: {tag.id}")
        return True, f"Тег '{name}' добавлен"
    except DuplicateKeyError:
        logger.warning(f"Тег '{name}' уже существует")
        return False, f"Тег '{name}' уже существует"
    except Exception as e:
        logger.error(f"Ошибка при добавлении тега '{name}': {e}")
        return False, f"Ошибка: {e}"

