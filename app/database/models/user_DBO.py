from pydantic import BaseModel, Field
from bson import ObjectId
from app.config.roles import Role


class User(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    telegram_tag: str = Field(..., min_length=1)
    telegram_id: int | None = Field(default=None)
    role: Role = Field(default=Role.USER)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}