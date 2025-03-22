import asyncio
import json
import os

import aiormq
import httpx
from aiormq.abc import AbstractConnection
from pamqp.commands import Basic

from . import responses as res
from ..bot import bot
from ..database.conference_db_operations import get_conference_by_link, add_recording_to_conference
from ..database.models.conference_DBO import Conference
from ..database.recording_db_operations import create_recording_by_conference_link
from ..database.user_db_operations import get_all_users, get_admins, get_user_by_id
from ..utils.logger import logger

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
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            print(f"Failed to download, status code: {response.status_code}")
            return None
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"File downloaded to {filepath}")
        return filepath


async def handle_responses(message: aiormq.abc.DeliveredMessage):
    body = message.body.decode().replace("'", '"').replace('b"', '"')
    print(f"Received response: {body}")
    await message.channel.basic_ack(delivery_tag=message.delivery.delivery_tag)
    try:
        msg: dict = json.loads(body)
        type = msg.get("type")
        body = msg.get("body")
        user_id = msg.get("user_id")  # USE USER_ID
        print(user_id)
        if type == res.Res.BUSY:
            print("Consumer is busy:", body)
            await message_to_all_admins(
                "⚠️ Ошибка записи \n\n "
                f"Ошибка записи конференции {body}: бот занят записью другой конференции "
                "и не может записать указанную."
            )
        elif type == res.Res.STARTED:
            print("Consumer started:", body)
            await message_to_all_admins(
                "🎦 Запись начата \n\n "
                f"Запись конференции {body} начата."
            )
        elif type == res.Res.SUCCEDED:
            filepath = msg.get("filepath")
            print("Consumer successfully finished recording:", body, filepath)
            await message_to_all_admins(
                "✅ Конференция записана успешно \n\n "
                f"Запись конференции {body} закончена и сохранена."
            )
            conference = await get_conference_by_link(body)
            if conference is not None:
                success, operation_msg, recording_id = await create_recording_by_conference_link(
                    conference.link, filepath
                )
                if success:
                    logger.warning(f"Successfully created recording with id {recording_id}: {operation_msg}")
                    success, operation_msg = await add_recording_to_conference(conference.id, recording_id)
                    if not success:
                        logger.warning(f"Error while adding recording with id {recording_id} "
                                       f"into the conference '{conference}' array: {operation_msg}")
                    else:
                        logger.warning(f"Successfully added recording with id {recording_id} "
                                       f"into the conference '{conference}' array: {operation_msg}")
                else:
                    logger.warning(f"Error while creating recording with conference link '{conference.link}' "
                                   f"and filepath '{filepath}': {operation_msg}")
            # filepath = await download_file(filepath)
            # admins = await get_admins()
            # found_admin = False
            # for admin in admins:
            #     if not found_admin:
            #         if admin.telegram_id is not None:
            #             found_admin = True
            #             await bot.send_document(
            #                 chat_id=admin.telegram_id,
            #                 document=filepath,
            #                 caption=f"Запись онлайн-конференции {body}"
            #             )
            #     else:
            #         await bot.send_video(
            #             chat_id=admin.telegram_id,
            #             video=filepath,
            #             caption=f"Запись онлайн-конференции {body}"
            #         )
            # # use filepath
            # # os.remove(filepath)
            filepath = get_link(msg.get("filepath"))
            print("Consumer successfuly finished recording:", body, filepath)
            # TODO use filepath
            # os.remove(filepath)
        elif type == res.Res.ERROR:
            print("Consumer finished with ERROR:", body)
            await message_to_all_admins(
                "⚠️ Ошибка записи \n\n "
                f"Не удалось записать конференцию {body}, произошла ошибка в процессе записи."
            )
        elif type == res.Req.SCREENSHOT:
            filepath = msg.get("filepath")
            print("Got screenshot:", filepath)
            filepath = await download_file(filepath)
            # TODO use filepath
            # os.remove(filepath)
        elif type == res.Req.TIME:
            print("Got current recording time:", body)
            # TODO write user

    except Exception as e:
        print(f"Consumer did not ack task: {body}\n{e}")


async def start_listening():
    print("Starting listening to queues...")
    connection = await get_connection()
    async with connection as conn:
        channel = await conn.channel()
        reses = channel.basic_consume(queue="gmeet_res", consumer_callback=handle_responses)
        await asyncio.gather(reses)
        print("Listeners are ready!")
        await asyncio.Future()
    print("Stopped listening to queues.")


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


async def message_to_all_admins(message: str):
    admins = await get_admins()
    for admin in admins:
        if admin.telegram_id is not None:
            await bot.send_message(
                chat_id=admin.telegram_id,
                message=message
            )
