import asyncio
from asyncio import StreamReader, subprocess
from os import getenv, remove, scandir
from time import time

import nodriver as uc

from .. import utils
from . import exceptions as ex

logger = utils.logger.setup_logger(__name__)

VIDEO = "output.mp4"


def SCREENSHOT() -> str:
    return f"screenshot_{int(time())}.png"


SCREEN_WIDTH = getenv("SCREEN_WIDTH")
SCREEN_HEIGHT = getenv("SCREEN_HEIGHT")

CMD_FFMPEG = 'ffmpeg -y -loglevel info -f x11grab -r 25 -i :0.0 \
    -f pulse -i default -channels 2 \
    -c:v libx264 -pix_fmt yuv420p -c:a aac \
    -vsync -1 -af aresample=async=-1 \
    -f segment -segment_time 600 -reset_timestamps 1 \
    -force_key_frames "expr:gte(t,n_forced*600)" -segment_format mp4 output/output_%03d.mp4'

CMD_CONCAT = f"ls output/*.mp4 | sed \"s|^output/|file '|;s|$|'|\" > output/list.txt \
    && ffmpeg -y -f concat -i output/list.txt -c copy {VIDEO}"

CMD_PULSE = "pulseaudio -D --system=false --exit-idle-time=-1 --disallow-exit --log-level=debug \
    && pactl load-module module-null-sink sink_name=virtual_sink \
    && pactl set-default-sink virtual_sink"
TIMEOUT = int(getenv("TIMEOUT"))
MIN_PEOPLE = int(getenv("MIN_PEOPLE"))
UPDATE_TIME = int(getenv("UPDATE_TIME"))
AWAIT_TIME = int(getenv("AWAIT_TIME"))
ATTEMPTS_RECOVERY = int(getenv("ATTEMPTS_RECOVERY"))


class GMeet:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__init()
        return cls.__instance

    def __init(self):
        print("Gmeet initializated.")
        self.__is_pulse_ready = False
        self.__start_time = 0
        self.__browser: uc.Browser = None
        self.__meet_page: uc.Tab = None

    async def __setup_browser(self):
        self.__browser = await uc.start(
            browser_args=[
                f"--window-size={SCREEN_WIDTH},{SCREEN_HEIGHT}",
                "--incognito",
            ]
        )

    async def __google_sign_in(self):
        logger.info("Signing in google account...")
        page = await self.__browser.get("https://accounts.google.com")
        await self.__browser.wait(3)
        email_field = await page.select("input[type=email]")
        await email_field.send_keys(getenv("GMAIL"))
        await self.__browser.wait(2)
        next_btn = await page.find("next")
        await next_btn.mouse_click()
        await self.__browser.wait(3)
        password_field = await page.select("input[type=password]")
        await password_field.send_keys(getenv("GPASS"))
        next_btn = await page.find("next")
        await next_btn.mouse_click()
        await self.__browser.wait(5)
        logger.info("Completed signing in google account.")

    async def __run_cmd(self, command, on_background=False):
        process = await asyncio.create_subprocess_shell(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=asyncio.subprocess.PIPE
        )

        async def read_stream(stream: StreamReader):
            while chunk := await stream.read(4096):
                logger.debug(chunk.decode())

        stdout_task = asyncio.create_task(read_stream(process.stdout))
        stderr_task = asyncio.create_task(read_stream(process.stderr))

        if on_background:
            logger.info(f"Cmd started with PID: {process.pid}")
            return process, stdout_task, stderr_task
        # Wait for the process to complete
        await asyncio.gather(stdout_task, stderr_task, process.wait())

    @property
    def is_running(self):
        return not (self.__browser is None)

    async def __run_pulse(self):
        logger.info("Running pulse...")
        try:
            await asyncio.wait_for(self.__run_cmd(CMD_PULSE), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            logger.error("Can't run cmd. Exiting it...")
            raise ex.ModuleException("pulse")
        self.__is_pulse_ready = True

    @property
    def recording_time(self) -> None | int:
        if not self.__start_time:
            return None
        return int(time() - self.__start_time)

    async def get_screenshot(self) -> None | str:
        logger.info("Getting screenshot...")
        if not self.__meet_page:
            return None
        return await self.__meet_page.save_screenshot(SCREENSHOT())

    async def __run_recording(self):
        logger.info("Start recording...")
        self.__start_time = time()
        ffmpeg = await self.__run_cmd(CMD_FFMPEG, True)
        left_people = 0
        attempts = 0
        while self.recording_time < AWAIT_TIME or left_people >= MIN_PEOPLE:
            await asyncio.sleep(UPDATE_TIME)
            try:
                element = await self.__meet_page.query_selector("div.uGOf1d")
                left_people = int(element.text) - 1
                attempts = 0
            except Exception:
                logger.warning("Can't get left people counter")
                left_people = MIN_PEOPLE
                attempts += 1
                if attempts == ATTEMPTS_RECOVERY:
                    logger.error("Something went wrong. Impossible to parse page!")
                    break

        logger.info("Stoped recording.")
        self.__start_time = 0
        return ffmpeg

    async def record_meet(self, meet_link: str) -> str:
        if self.is_running:
            raise ex.AlreadyRunException()
        logger.info(f"Recoring for link: {meet_link}")
        if not self.__is_pulse_ready:
            await self.__run_pulse()

        await self.__setup_browser()
        await self.__google_sign_in()
        self.__meet_page = await self.__browser.get(meet_link)
        await self.__browser.wait(5)
        next_btn = await self.__meet_page.find("join now")
        await next_btn.mouse_click()
        await self.__browser.wait(5)

        # await asyncio.sleep(31 * 60)
        ffmpeg = await self.__run_recording()

        exit_btn = await self.__meet_page.find_element_by_text("leave call")
        await exit_btn.mouse_click()
        await self.__browser.wait(2)
        self.__browser.stop()
        self.__meet_page = None
        # return
        try:
            ffmpeg[0].stdin.write(b"q")
            logger.info("FFmpeg terminated. Waiting...")
            await ffmpeg[0].stdin.drain()
            await asyncio.gather(ffmpeg[0].wait(), ffmpeg[1], ffmpeg[2])
            logger.info("Start concatination...")
            await asyncio.wait_for(self.__run_cmd(CMD_CONCAT), timeout=TIMEOUT)
            return VIDEO
        except asyncio.TimeoutError:
            logger.error("Can't conact videos. Raise error.")
            raise ex.ModuleException("ffmpeg")
        finally:
            with scandir("output") as it:
                for entry in it:
                    if entry.is_file():
                        remove(entry)
            self.__browser = None
