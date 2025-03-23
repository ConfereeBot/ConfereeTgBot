from pydantic import BaseModel, Field
from bson import ObjectId
from typing import List, Optional
import time


class Conference(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    tag_id: ObjectId = Field(...)
    link: str = Field(..., min_length=1)
    next_meeting_timestamp: int | None = Field(default_factory=lambda: int(time.time()))  # Unix timestamp in seconds
    recordings: List[ObjectId] = Field(default_factory=list)
    timezone: int = Field(...)  # Timezone offset from UTC
    periodicity: Optional[int] = Field(default=None)  # Periodicity in weeks (1, 2, or None)
    users_queue_to_get_screenshot: List[ObjectId] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
