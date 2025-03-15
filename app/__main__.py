import asyncio
import os
from tomllib import load

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.config.config import OWNERS
from app.database.database import db
from app.database.user_db_operations import ensure_owner_role
from app.middlewares.logging import LoggingMiddleware
from app.utils.logger import setup_logger
from app.roles.admin.admin import admin
from app.roles.user.user_cmds import user
from app.roles.owner.owner import owner

import app.roles.user.callbacks_enum
import app.roles.user.main_actions.tags_management.handlers.tags_create
import app.roles.user.main_actions.tags_management.handlers.tags_read
import app.roles.user.main_actions.tags_management.handlers.tags_update
import app.roles.user.main_actions.tags_management.handlers.tags_delete
import app.roles.user.main_actions.recording_search.recording_search
import app.roles.user.main_actions.recording_create.recording_create
import app.roles.user.main_actions.admins_management.admins_management
import app.roles.user.main_actions.shared_callbacks

logger = setup_logger(__name__)


async def ensure_owners_in_db():
    """Проверяет и устанавливает роль owner для пользователей из OWNERS."""
    for owner_tag in OWNERS:
        success, response = await ensure_owner_role(owner_tag)
        if success:
            logger.info(response)
        else:
            logger.error(response)


async def main():
    dp = Dispatcher()
    dp.include_routers(user, admin, owner)
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(LoggingMiddleware())

    logger.info(f"User router message handlers: {user.message.handlers}")
    logger.info(f"User router callback handlers: {user.callback_query.handlers}")

    bot = Bot(
        token=os.getenv("TOKEN_BOT"),
        default=DefaultBotProperties(parse_mode="html"),
    )

    logger.info("Старт бота")
    await db.ping()  # Проверка подключения к БД
    await db.setup_indexes()  # Настройка индексов
    await ensure_owners_in_db()  # Проверка и установка владельцев
    await dp.start_polling(bot)  # Запуск бота


def get_version():
    with open("pyproject.toml", "rb") as file:
        data = load(file)
    return data["tool"]["poetry"]["version"]


if __name__ == "__main__":
    try:
        logger.info(f"Запуск приложения версии {get_version()}")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Работа приложения прервана")
    except Exception as ex:
        logger.critical(ex)