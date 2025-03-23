import asyncio

from aiogram import Dispatcher
from tomllib import load

import app.rabbitmq as mq
from app.bot import bot
from app.config.config import OWNERS
from app.database.database import db
from app.database.db_operations.user_db_operations import ensure_owner_role
from app.middlewares.logging import LoggingMiddleware
from app.roles.admin.admin import admin
from app.roles.owner.owner import owner
from app.roles.user.user_cmds import user
from app.utils.logger import setup_logger

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
    logger.info(f"Owner router message handlers: {owner.message.handlers}")
    logger.info(f"Owner router callback handlers: {owner.callback_query.handlers}")

    logger.info("Старт бота")
    await db.ping()  # Проверка подключения к БД
    await db.setup_indexes()  # Настройка индексов
    await ensure_owners_in_db()  # Проверка и установка владельцев

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
