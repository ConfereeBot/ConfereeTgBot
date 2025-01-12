import asyncio

from .. import utils

logger = utils.logger.setup_logger(__name__)


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")
    i = 0
    while True:
        await asyncio.sleep(2)
        logger.info(i)
        i += 1
