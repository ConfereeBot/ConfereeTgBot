import asyncio
import json
import pickle
import subprocess
from os import getenv, path

import nodriver as uc

from .. import utils

logger = utils.logger.setup_logger(__name__)


async def setup_driver() -> uc.Browser:
    driver = await uc.start(browser_args=["--window-size=1920,1080", "--incognito"])
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


async def record_meet(meet_link: str):
    logger.info(f"Recoring for link: {meet_link}")

    await run_cmd(
        "pulseaudio -D --system=false --exit-idle-time=-1 --disallow-exit --log-level=debug \
        && pactl load-module module-null-sink sink_name=virtual_sink \
        && pactl set-default-sink virtual_sink"
    )
    driver = await setup_driver()
    await google_sign_in(driver)
    page = await driver.get(meet_link)
    await driver.wait(5)
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
