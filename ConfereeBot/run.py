import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.handlers import router
from config import TOKEN


bot = Bot(token=TOKEN)
dispatcher = Dispatcher()


async def main():
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
