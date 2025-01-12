import asyncio

import undetected_chromedriver as uc

from .. import utils

logger = utils.logger.setup_logger(__name__)


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")
    options = uc.ChromeOptions()

    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")

    driver = uc.Chrome(use_subprocess=False, options=options)
    driver.get("https://meet.google.com/wsc-ywte-njv")
    logger.info(driver.page_source)
    await asyncio.sleep(60)
    logger.info("WINNING!")
