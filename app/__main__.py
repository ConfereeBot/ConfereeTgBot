import asyncio
import os
from tomllib import load

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.database.database import db
from app.middlewares.logging import LoggingMiddleware
from app.roles import admin, owner, user
from app.utils import setup_logger

logger = setup_logger(__name__)


async def main():
    dp = Dispatcher()
    dp.include_routers(admin, owner, user)
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(LoggingMiddleware())

    bot = Bot(
        token=os.getenv("TOKEN_BOT"),
        default=DefaultBotProperties(parse_mode="html"),
    )

    logger.info("Старт бота")
    await db.ping()  # check db connectivity
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
