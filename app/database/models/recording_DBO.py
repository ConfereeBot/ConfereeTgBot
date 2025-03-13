from pydantic import BaseModel, Field
from bson import ObjectId
from app.database.models.tag_DBO import Tag
import time


class Recording(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    tag: Tag = Field(...)
    link: str = Field(..., min_length=1)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}