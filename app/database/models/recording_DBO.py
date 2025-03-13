from pydantic import BaseModel, Field
from bson import ObjectId


class Recording(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    meeting_id: ObjectId = Field(...)
    link: str = Field(..., min_length=1)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
