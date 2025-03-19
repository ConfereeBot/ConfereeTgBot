import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=os.getenv("TOKEN_BOT"),
    default=DefaultBotProperties(parse_mode="html"),
)
