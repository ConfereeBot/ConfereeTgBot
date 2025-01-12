from asyncio import sleep
from os import getenv

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .. import utils

logger = utils.logger.setup_logger(__name__)


async def setup_driver() -> uc.Chrome:
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

    return uc.Chrome(use_subprocess=False, options=options)


async def google_sign_in(driver: uc.Chrome):
    logger.info("Signing in google account...")
    driver.get("https://accounts.google.com")
    await sleep(1)
    email_field = driver.find_element(By.NAME, "identifier")
    email_field.send_keys(getenv("GMAIL"))
    await sleep(2)
    email_field.send_keys(Keys.RETURN)
    await sleep(3)
    password_field = driver.find_element(By.NAME, "Passwd")
    password_field.click()
    password_field.send_keys(getenv("GPASS"))
    password_field.send_keys(Keys.RETURN)
    await sleep(5)
    logger.info("Completed signing in google account.")


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")
    driver = await setup_driver()
    await google_sign_in(driver)

    driver.get(meet_link)
    driver.quit()
