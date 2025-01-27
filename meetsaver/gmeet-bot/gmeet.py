import asyncio
from asyncio import subprocess
from os import getenv

import nodriver as uc

from .. import utils

logger = utils.logger.setup_logger(__name__)


FILENAME = "output.mp4"
CMD_FFMPEG = f"ffmpeg -y -loglevel warning -framerate 30 \
    -f x11grab -i :0 -f pulse -i virtual_sink.monitor -ac 2 -b:a 192k {FILENAME}"
CMD_PULSE = "pulseaudio -D --system=false --exit-idle-time=-1 --disallow-exit --log-level=debug \
    && pactl load-module module-null-sink sink_name=virtual_sink \
    && pactl set-default-sink virtual_sink"
TIMEOUT = 5


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


async def record_meet(meet_link: str) -> None | str:
    logger.info(f"Recoring for link: {meet_link}")
    try:
        stdout, stderr = await asyncio.wait_for(run_cmd(CMD_PULSE), timeout=TIMEOUT)
        logger.debug(stderr)
    except asyncio.TimeoutError:
        logger.error("Can't run cmd. Exiting it...")
        return None

    driver = await setup_driver()
    await google_sign_in(driver)
    page = await driver.get(meet_link)
    await driver.wait(5)
    next_btn = await page.find("join now")
    await next_btn.mouse_click()
    await driver.wait(5)

    logger.info("Start recording...")
    ffmpeg = await run_cmd(CMD_FFMPEG, True)
    await asyncio.sleep(10)
    logger.info("Stoped recording.")

    exit_btn = await page.find_element_by_text("leave call")
    await exit_btn.mouse_click()
    await driver.wait(2)
    driver.stop()

    try:
        ffmpeg.stdin.write(b"q")
        logger.debug("Terminated. Waiting...")
        await ffmpeg.stdin.drain()
        stdout, stderr = await asyncio.wait_for(ffmpeg.communicate(), timeout=TIMEOUT)
        logger.debug(stderr)
        return FILENAME
    except asyncio.TimeoutError:
        logger.error("Can't terminate ffmpeg. Killing it...")
        ffmpeg.kill()


async def run_cmd(command, on_background=False):
    process = await asyncio.create_subprocess_shell(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=asyncio.subprocess.PIPE
    )
    if on_background:
        logger.info(f"Cmd started with PID: {process.pid}")
        return process
    # Wait for the process to complete
    stdout, stderr = await process.communicate()
    return stdout, stderr
