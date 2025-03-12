from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId


class Admin(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    username: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
