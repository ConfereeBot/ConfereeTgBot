from pydantic import BaseModel, Field
from bson import ObjectId


class Tag(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str = Field(..., min_length=1, max_length=32)
    is_archived: bool = Field(default=False)
    # 32 chars is recommended for inline. More chars may go out of screen due to small phone screen

    class Config:
        arbitrary_types_allowed = True  # Enabling ObjectId
        json_encoders = {ObjectId: str}  # Converting ObjectId into string for JSON
