from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config.roles import Role
from app.filters import RoleFilter
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

owner = Router()
owner.message.filter(RoleFilter(Role.OWNER))
