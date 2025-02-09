from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.utils import setup_logger

logger = setup_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: TelegramObject, data: Dict[str, Any]):
        user_id = event.from_user.id
        if isinstance(event, Message):
            logger.debug(f"Message (user_id={user_id}): {event.text}")
        elif isinstance(event, CallbackQuery):
            logger.debug(f"CallbackQuery (user_id={user_id}): {event.data}")
        return await handler(event, data)
