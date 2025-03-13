from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.config import MONGODB_URI, DB_NAME
from app.database.models.tag_DBO import Tag
from app.database.models.admin_DBO import Admin


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DB_NAME]

    async def ping(self):
        await self.db.command("ping")
        print("MongoDB connection successful")

    async def setup_indexes(self):
        await self.db["tags"].create_index("name", unique=True)
        await self.db["admins"].create_index("username", unique=True)
        await self.db["recordings"].create_index("meeting_id")
        await self.db["conferences"].create_index("link", unique=True)

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

    async def get_all_admins(self) -> List[Admin]:
        admins_collection = self.db["admins"]
        admins = []
        async for admin_doc in admins_collection.find():
            admins.append(Admin(**admin_doc))
        return admins


db = Database()
