import asyncio
import os
from tomllib import load

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.database.database import db
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


async def main():
    dp = Dispatcher()
    dp.include_routers(user, admin, owner)
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(LoggingMiddleware())

    # logger.info(user.)
    logger.info(f"User router message handlers: {user.message.handlers}")
    logger.info(f"User router callback handlers: {user.callback_query.handlers}")

    bot = Bot(
        token=os.getenv("TOKEN_BOT"),
        default=DefaultBotProperties(parse_mode="html"),
    )

    logger.info("Старт бота")
    await db.ping()  # check db connectivity
    await db.setup_indexes()  # setup db indexes
    await dp.start_polling(bot)  # start bot


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
