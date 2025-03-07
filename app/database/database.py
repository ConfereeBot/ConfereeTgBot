from motor.motor_asyncio import AsyncIOMotorClient
from app.config.config import MONGODB_URI, DB_NAME


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DB_NAME]

    async def ping(self):
        # check connection
        await self.db.command("ping")
        print("MongoDB connection successful")


db = Database()
