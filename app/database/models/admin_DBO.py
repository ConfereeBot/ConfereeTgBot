from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId


class Admin(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    username: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
