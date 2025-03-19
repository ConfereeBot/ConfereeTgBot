from aiogram import Router

from app.config.roles import Role
from app.filters import RoleFilter

owner = Router()
owner.message.filter(RoleFilter(Role.OWNER))
owner.callback_query.filter(RoleFilter(Role.OWNER))
