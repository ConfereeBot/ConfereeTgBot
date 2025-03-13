from pydantic import BaseModel, Field
from bson import ObjectId
from typing import List
import time


class Conference(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    tag_id: ObjectId = Field(...)
    link: str = Field(..., min_length=1)
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    recordings: List[ObjectId] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
