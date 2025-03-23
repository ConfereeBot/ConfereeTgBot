import asyncio
import json
import os

import aiormq
import httpx
from aiormq.abc import AbstractConnection
from pamqp.commands import Basic

from . import responses as res
from ..bot import bot
from app.database.db_operations.conference_db_operations import get_conference_by_link, add_recording_to_conference, \
    update_conference_timestamp
from ..database.models.conference_DBO import Conference
from app.database.db_operations.recording_db_operations import create_recording_by_conference_link
from app.database.db_operations.tag_db_operations import get_tag_by_id
from app.database.db_operations.user_db_operations import get_admins, get_owners
from ..utils.logger import logger
from datetime import datetime
from aiogram.types import FSInputFile
from datetime import timezone as datetime_timezone

connection: AbstractConnection | None = None


async def get_connection() -> AbstractConnection:
    global connection
    if connection and not connection.is_closed:
        return connection
    connection = await aiormq.connect(os.getenv("AMQP"))
    return connection


async def schedule_task(link: str, in_secs: int):
    print(f"Scheduled new task ({link}) in {in_secs} sec")
    connection = await get_connection()
    channel = await connection.channel()
    await channel.basic_publish(
        body=link.encode(),
        exchange="conferee_direct",
        routing_key="gmeet_schedule",
        properties=Basic.Properties(expiration=str(in_secs * 1000)),
    )


async def manage_active_task(command: res.Req, user_id: int):
    print(f"Manage active task: <{command}>")
    connection = await get_connection()
    channel = await connection.channel()
    await channel.basic_publish(
        body=res.prepare(command, "", user_id),
        exchange="conferee_direct",
        routing_key="gmeet_manage",
    )


def get_link(filepath):
    web = os.getenv("WEB_SERVER")
    return web + filepath


async def download_file(filepath):
    url = get_link(filepath)
    logger.info(f"download_file: got url {url} from get_link({filepath})")
    async with httpx.AsyncClient() as client:
        logger.info(f"download_file: sending request client.get({url})")
        response = await client.get(url)
        logger.info(f"download_file: received a response: {response}")
        if response.status_code != 200:
            logger.info(f"Failed to download, status code: {response.status_code}")
            return None
        logger.info("download_file: response code is 200, OK!")
        with open(filepath, "wb") as f:
            f.write(response.content)
        logger.info(f"File downloaded to {filepath}")
        return filepath


async def update_conference_meeting_datetime(conference: Conference) -> tuple[bool, str]:
    if conference.periodicity is None:
        return await update_conference_timestamp(conference.id, None)
    else:
        next_meeting_timestamp = conference.next_meeting_timestamp + conference.periodicity * 7 * 24 * 60 * 60
        logger.info(f"Next meeting scheduled on {next_meeting_timestamp}, which is {conference.next_meeting_timestamp} + {conference.periodicity} week")
        success, msg = await update_conference_timestamp(conference.id, next_meeting_timestamp)
        if not success:
            return False, f"Error while updating conference timestamp: {msg}"
        current_time = int(datetime.now(datetime_timezone.utc).timestamp())
        secs_before_meeting = next_meeting_timestamp - current_time
        logger.info(f"Scheduling task with link {conference.link} for broker: start in {secs_before_meeting}s, as now it is {current_time} and in planned it is {next_meeting_timestamp}")
        await schedule_task(conference.link, secs_before_meeting)
        return True, f"Successfully scheduled new task for broker on link {conference.link}, start in {secs_before_meeting}s"


async def handle_responses(message: aiormq.abc.DeliveredMessage):
    body = message.body.decode().replace("'", '"').replace('b"', '"')
    print(f"Received response: {body}")
    await message.channel.basic_ack(delivery_tag=message.delivery.delivery_tag)
    try:
        msg: dict = json.loads(body)
        response_type = msg.get("type")
        body = msg.get("body")
        user_id = msg.get("user_id")  # USE USER_ID, only for SCREENSHOT and TIME
        if response_type == res.Res.BUSY:
            print("Consumer is busy:", body)
            await message_to_all_admins_and_owners(
                message="⚠️ Ошибка записи!\n\n "
                f"Ошибка записи конференции {body}: бот занят записью другой конференции "
                "и не может записать указанную."
            )
        elif response_type == res.Res.STARTED:
            print("Consumer started:", body)
            await message_to_all_admins_and_owners(
                "🎦 Запись начата.\n\n "
                f"Запись конференции {body} начата."
            )
        elif response_type == res.Res.SUCCEDED:
            filepath = get_link(msg.get("filepath"))
            logger.info(f"Got recording filepath: '{filepath}', the filepath itself in msg is '{msg.get("filepath")}'")
            print("Consumer successfully finished recording:", body, filepath)
            conference = await get_conference_by_link(body)
            if conference is not None:
                conference_tag = await get_tag_by_id(str(conference.tag_id))
            else:
                conference_tag = None
            if conference_tag is not None:
                await message_to_all_admins_and_owners(
                    "✅ Конференция записана успешно!\n\n "
                    f"Запись конференции с тегом '{conference_tag.name}' и ссылкой '{body}' закончена и сохранена."
                )
            else:
                await message_to_all_admins_and_owners(
                    "✅ Конференция записана успешно!\n\n "
                    f"Запись конференции с ссылкой '{body}' закончена и сохранена."
                )
            if conference is not None:
                success, msg = await update_conference_meeting_datetime(conference=conference)
                if not success:
                    logger.warning(msg)
                success, operation_msg, recording_id, recording = await create_recording_by_conference_link(
                    conference_link=conference.link,
                    recording_link=filepath
                )
                if success:
                    logger.warning(f"Successfully created recording with id {recording_id}: {operation_msg}")
                    success, operation_msg = await add_recording_to_conference(conference.id, recording_id)
                    if not success:
                        logger.warning(f"Error while adding recording with id {recording_id} "
                                       f"into the conference '{conference}' array: {operation_msg}")
                    else:
                        recording.link = filepath
                        logger.warning(f"Successfully added recording with id {recording_id} "
                                       f"into the conference '{conference}' array: {operation_msg} "
                                       f"and the download link {filepath} into recording.")
                else:
                    logger.warning(f"Error while creating recording with conference link '{conference.link}' "
                                   f"and filepath '{filepath}': {operation_msg}")
        elif response_type == res.Res.ERROR:
            print("Consumer finished with ERROR:", body)
            await message_to_all_admins_and_owners(
                "⚠️ Ошибка записи.\n\n "
                f"Не удалось записать конференцию {body}, произошла ошибка в процессе записи."
            )
        elif response_type == res.Req.SCREENSHOT:
            filepath = msg.get("filepath")
            print("Got screenshot:", filepath)
            try:
                filepath = await download_file(filepath)
            except Exception as e:
                logger.warning(f"Exception while downloading file from {filepath}: '{e}'")
                return
            photo = FSInputFile(filepath)
            await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=f"✔ Запрошенный скриншот происходящего в конференции {body} готов!"
            )
            os.remove(filepath)
        elif response_type == res.Req.TIME:
            print("Got current recording time:", body)
            secs_from_rec_start = msg.get("filepath")
            await bot.send_message(
                chat_id=user_id,
                text=f"✔ Готов ответ на запрос о времени записи конференции {body}:\n\n"
                     f"Запись ведётся уже {secs_from_rec_start // 60 // 60}ч "
                     f"{(secs_from_rec_start // 60) % 60}м "
                     f"{secs_from_rec_start% 60}с"
            )

    except Exception as e:
        print(f"Consumer did not ack task: {body}\n{e}, {type(e)}")


async def start_listening():
    logger.info("Starting listening to queues...")
    connection = await get_connection()
    async with connection as conn:
        channel = await conn.channel()
        reses = channel.basic_consume(queue="gmeet_res", consumer_callback=handle_responses)
        await asyncio.gather(reses)
        logger.info("Listeners are ready!")
        await asyncio.Future()
    logger.info("Stopped listening to queues.")


async def decline_task(link: str):
    connection = await get_connection()
    channel = await connection.channel()
    while True:
        message = await channel.basic_get("gmeet_schedule")
        body = message.body.decode()
        if not body:
            break
        if body == link:
            print(f"Task ({link}) canceled.")
            await message.channel.basic_ack(delivery_tag=message.delivery.delivery_tag)


async def message_to_all_admins_and_owners(message: str):
    admins = await get_admins()
    for admin in admins:
        if admin.telegram_id is not None:
            await bot.send_message(
                chat_id=admin.telegram_id,
                text=message,
                disable_notification=True,
            )
    owners = await get_owners()
    for owner in owners:
        if owner.telegram_id is not None:
            await bot.send_message(
                chat_id=owner.telegram_id,
                text=message,
                disable_notification=True,
            )
