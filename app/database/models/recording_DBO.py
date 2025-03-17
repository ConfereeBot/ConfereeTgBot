from pydantic import BaseModel, Field
from bson import ObjectId
from time import time


class Recording(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    conference_id: ObjectId = Field(...)
    link: str = Field(..., min_length=1)
    timestamp: int = Field(default_factory=lambda: int(time()))

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
