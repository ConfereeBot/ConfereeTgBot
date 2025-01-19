import asyncio
import pickle
import subprocess
from asyncio import sleep
from os import getenv, path

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
    options.add_argument("--disable-features=IdentityConsistency")

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


async def first_open(meet_link: str):
    driver = await setup_driver()
    await google_sign_in(driver)

    driver.get(meet_link)
    await sleep(5)
    with open("cookies.pkl", "wb") as cookies_file:
        pickle.dump(driver.get_cookies(), cookies_file)
    driver.quit()


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")

    if not path.exists("cookies.pkl"):
        await first_open()
    driver = await setup_driver()
    driver.get(meet_link)
    await sleep(5)
    with open("cookies.pkl", "rb") as cookies_file:
        cookies = pickle.load(cookies_file)
        for cookie in cookies:
            driver.add_cookie(cookie)
    driver.refresh()
    await sleep(5)
    driver.find_element(
        By.XPATH,
        '//*[@id="yDmH0d"]/c-wiz/div/div/div[37]/div[4]/div/div[2]/\
div[4]/div/div/div[2]/div[1]/div[2]/div[1]/div/div/button/span[6]',
    ).click()
    await sleep(5)
    logger.info("Start recording...")
    await run_cmd(
        "pulseaudio -D --system=false --exit-idle-time=-1 --disallow-exit \
&& pactl load-module module-null-sink sink_name=virtual_sound"
    )
    await run_cmd(
        "ffmpeg -y -framerate 30 \
-f x11grab -i :0 -f pulse -i virtual_sound.monitor -t 10 \
-analyzeduration 1000000 -buffer_size 2048 output.mp4"
    )
    logger.info("Stoped recording.")
    driver.find_element(
        By.XPATH,
        '//*[@id="yDmH0d"]/c-wiz/div/div/div[34]/div[4]/\
div[10]/div/div/div[2]/div/div[8]/span/button/div',
    ).click()
    await sleep(2)
    driver.quit()


async def run_cmd(command):
    process = await asyncio.create_subprocess_shell(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Wait for the process to complete
    stdout, stderr = await process.communicate()
    logger.debug(stderr)

    return stdout, stderr
