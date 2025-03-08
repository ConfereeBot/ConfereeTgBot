from typing import List

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.config import MONGODB_URI, DB_NAME
from app.database.models.tag_DBO import Tag


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

    async def get_all_tags(self) -> List[Tag]:
        tags_collection = self.db["tags"]
        tags = []
        async for tag_doc in tags_collection.find():
            tags.append(Tag(**tag_doc))
        return tags


db = Database()
