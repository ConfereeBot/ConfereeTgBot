import asyncio

import undetected_chromedriver as uc

from .. import utils

logger = utils.logger.setup_logger(__name__)


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")
    uc.Chrome()
    logger.info("WINNING!")
