import asyncio
import os
from tomllib import load

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import app.rabbitmq as mq
import app.roles.user.callbacks_enum
import app.roles.owner.admins_management.admins_management
import app.roles.user.main_actions.recording_create.recording_create
import app.roles.user.main_actions.recording_search.recording_search
import app.roles.user.main_actions.shared_callbacks
import app.roles.admin.tags_management.handlers.tags_create
import app.roles.admin.tags_management.handlers.tags_delete
import app.roles.admin.tags_management.handlers.tags_read
import app.roles.admin.tags_management.handlers.tags_update
from app.database.database import db
from app.middlewares.logging import LoggingMiddleware
from app.roles.admin.admin import admin
from app.roles.owner.owner import owner
from app.roles.user.user_cmds import user
from app.config.config import OWNERS
from app.database.database import db
from app.database.user_db_operations import ensure_owner_role
from app.middlewares.logging import LoggingMiddleware
from app.utils.logger import setup_logger
from app.roles.admin.admin import admin
from app.roles.user.user_cmds import user
from app.roles.owner.owner import owner

from app.roles.admin.tags_management.handlers import tags_create
from app.roles.admin.tags_management.handlers import tags_read
from app.roles.admin.tags_management.handlers import tags_update
from app.roles.admin.tags_management.handlers import tags_delete
from app.roles.owner.admins_management import admins_management
from app.roles.user.main_actions import shared_callbacks
from app.roles.user.main_actions.recording_search import recording_search
from app.roles.user.main_actions.recording_create import recording_create

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
    await db.ping()  # check db connectivity
    await db.setup_indexes()  # setup db indexes

    mq_task = asyncio.create_task(mq.func.start_listening())
    bot_task = asyncio.create_task(dp.start_polling(bot))
    await asyncio.gather(mq_task, bot_task)  # start bot & rabbitmq listener


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


""" USAGE

Всё обрабатывай в mq.func.handle_responses, там я написал # TODO для твоего кода

await mq.func.schedule_task("https://meet.google.com/qwe-qwe-qwe", 0)   schedule task in n secs
await mq.func.manage_active_task(mq.responses.Req.TIME)                 request for current recording time
await mq.func.manage_active_task(mq.responses.Req.SCREENSHOT)           request for screenshot
await mq.func.decline_task("https://meet.google.com/qwe-qwe-qwe")       delete task from schedule
"""
