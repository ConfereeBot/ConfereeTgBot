import asyncio
import json
import pickle
import subprocess
from os import getenv, path

import nodriver as uc

from .. import utils

logger = utils.logger.setup_logger(__name__)

COOKIE_FILE_NAME = ".session.dat"


async def setup_driver() -> uc.Browser:
    driver = await uc.start()
    return driver


async def google_sign_in(driver: uc.Browser):
    logger.info("Signing in google account...")
    page = await driver.get("https://accounts.google.com")
    await driver.wait(3)
    email_field = await page.select("input[type=email]")
    await email_field.send_keys(getenv("GMAIL"))
    await driver.wait(2)
    next_btn = await page.find("next")
    await next_btn.mouse_click()
    await driver.wait(3)
    password_field = await page.select("input[type=password]")
    await password_field.send_keys(getenv("GPASS"))
    next_btn = await page.find("next")
    await next_btn.mouse_click()
    await driver.wait(5)
    logger.info("Completed signing in google account.")


async def first_open():
    driver = await setup_driver()
    await google_sign_in(driver)
    await save_cookies(driver)
    driver.stop()


async def save_cookies(driver: uc.Browser):
    try:
        await driver.cookies.save(COOKIE_FILE_NAME)
        logger.info("Cookies saved.")
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")


async def load_cookies(driver: uc.Browser, page: uc.Tab):
    try:
        await driver.cookies.load(COOKIE_FILE_NAME)
        await page.reload()
        await driver.wait(5)
        logger.info("Cookies loaded.")
        return True
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to load cookies: {e}")
    except FileNotFoundError:
        logger.error("Cookie file does not exist.")

    return False


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")

    # if not path.exists(COOKIE_FILE_NAME):
    # await first_open()
    await run_cmd(
        "pulseaudio -D --system=false --exit-idle-time=-1 --disallow-exit --log-level=debug \
&& pactl load-module module-null-sink sink_name=virtual_sink \
&& pactl set-default-sink virtual_sink"
    )
    driver = await setup_driver()
    await google_sign_in(driver)
    page = await driver.get(meet_link)
    await page.maximize()
    await driver.wait(5)
    # if not await load_cookies(driver, page):
    #     logger.warning("Can't load cookies. Exiting...")
    #     return
    next_btn = await page.find("join now")
    await next_btn.mouse_click()
    await driver.wait(5)

    logger.info("Start recording...")
    await run_cmd(
        "ffmpeg -y -loglevel warning -framerate 30 \
-f x11grab -i :0 -f pulse -i virtual_sink.monitor -t 10 -ac 2 -b:a 192k output.mp4"
    )
    logger.info("Stoped recording.")

    exit_btn = await page.find_element_by_text("leave call")
    await exit_btn.mouse_click()
    await driver.wait(2)
    driver.stop()


async def run_cmd(command):
    process = await asyncio.create_subprocess_shell(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Wait for the process to complete
    stdout, stderr = await process.communicate()
    logger.debug(stderr)

    return stdout, stderr
