import asyncio
import json
import os

import aiormq
import httpx
from aiormq.abc import AbstractConnection
from pamqp.commands import Basic

from . import responses as res

connection: AbstractConnection = None


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


async def manage_active_task(command: res.Req):
    print(f"Manage active task: <{command}>")
    connection = await get_connection()
    channel = await connection.channel()
    await channel.basic_publish(
        body=res.prepare(command, ""),
        exchange="conferee_direct",
        routing_key="gmeet_manage",
    )


async def download_file(filepath):
    web = os.getenv("WEB_SERVER")
    url = web + filepath
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
        if type == res.Res.BUSY:
            print("Consumer is busy:", body)
            # TODO write user
        elif type == res.Res.STARTED:
            print("Consumer started:", body)
        elif type == res.Res.SUCCEDED:
            filepath = msg.get("filepath")
            print("Consumer successfuly finished recording:", body, filepath)
            filepath = await download_file(filepath)
            # TODO use filepath
            # os.remove(filepath)
        elif type == res.Res.ERROR:
            print("Consumer finished with ERROR:", body)
            # TODO write user
        elif type == res.Req.SCREENSHOT:
            print("Got screenshot:", body)
            filepath = await download_file(body)
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
