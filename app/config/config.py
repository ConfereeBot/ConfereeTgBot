import os
from typing import List

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "conferee_bot_db"

OWNERS: List[str] = os.getenv("OWNERS", "").split(",") if os.getenv("OWNERS") else []
OWNERS = [owner.strip() for owner in OWNERS if owner.strip()]
