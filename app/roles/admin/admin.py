from aiogram import Router

from app.config.roles import Role
from app.filters import RoleFilter

admin = Router()
admin.message.filter(RoleFilter(Role.ADMIN))
admin.callback_query.filter(RoleFilter(Role.ADMIN))
