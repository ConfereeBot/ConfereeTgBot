from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import labels
from app.database.conference_db_operations import get_conferences_by_tag, get_conference_by_link
from app.database.recording_db_operations import get_recording_by_id
from app.database.tag_db_operations import get_tag_by_id
from app.keyboards import (
    choose_recordings_search_method_keyboard as recordings_keyboard,
    inline_active_tag_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.user_cmds import logger, user


class RecordingSearchStates(StatesGroup):
    waiting_for_meet_link = State()


@user.message(F.text == labels.GET_RECORD)
async def get_recording(message: Message):
    logger.info("get_recordings_call")
    await message.answer(
        text="How do you want to find a recording: by tag or by link?",
        reply_markup=recordings_keyboard,
    )


@user.callback_query(F.data == Callbacks.get_recording_by_tag_callback)
async def get_recording_by_tag(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Select the desired tag:",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_search_mode_callback,
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
            on_archived_clicked_callback=None,
            on_item_create_clicked_callback=None,
        ),
    )


@user.callback_query(F.data.startswith(Callbacks.tag_clicked_in_search_mode_callback))
async def process_tag_selection(callback: CallbackQuery):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Error: tag not selected!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Error: tag not found in database!", show_alert=True)
        return

    conferences = await get_conferences_by_tag(tag_id)
    if not conferences:
        await callback.message.edit_text(
            text=f"No conferences found with tag '{tag.name}'.",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    else:
        response = f"Found conferences with tag '{tag.name}':\n\n"
        for conference in conferences:
            timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            response += f"Conference: {conference.link}\nDate: {timestamp_str}\nID: {conference.id}\n"
            if conference.recordings:
                response += "Recordings:\n"
                for recording_id in conference.recordings:
                    recording = await get_recording_by_id(str(recording_id))
                    if recording:
                        response += f"  - {recording.link} (ID: {recording.id})\n"
                    else:
                        response += f"  - Recording with ID {recording_id} not found\n"
            else:
                response += "No recordings.\n"
            response += "\n"
        await callback.message.edit_text(
            text=response.strip(),
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await callback.answer("")


@user.callback_query(F.data == Callbacks.get_recording_by_link_callback)
async def start_recording_by_link(callback: CallbackQuery, state: FSMContext):
    await callback.answer("")
    await callback.message.edit_text(
        text="Enter the Google Meet conference link:",
        reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
    )
    await state.set_state(RecordingSearchStates.waiting_for_meet_link)


@user.message(RecordingSearchStates.waiting_for_meet_link)
async def process_meet_link(message: Message, state: FSMContext):
    meet_link = message.text.strip()
    conference = await get_conference_by_link(meet_link)
    if conference:
        tag = await get_tag_by_id(str(conference.tag_id))  # Получаем тег по tag_id
        tag_name = tag.name if tag else "Unknown Tag"
        timestamp_str = datetime.fromtimestamp(conference.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        response = f"Found conference:\nLink: {conference.link}\nTag: {tag_name}\nDate: {timestamp_str}\nID: {conference.id}\n"
        if conference.recordings:
            response += "Recordings:\n"
            for recording_id in conference.recordings:
                recording = await get_recording_by_id(str(recording_id))
                if recording:
                    response += f"  - {recording.link} (ID: {recording.id})\n"
                else:
                    response += f"  - Recording with ID {recording_id} not found\n"
        else:
            response += "No recordings."
        await message.answer(
            text=response.strip(),
            reply_markup=main_actions_keyboard,
        )
    else:
        await message.answer(
            text=f"Conference with link '{meet_link}' not found!",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    await state.clear()


@user.callback_query(F.data == Callbacks.cancel_primary_action_callback)
async def on_cancel_primary_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("")
    await callback.message.delete()
    await callback.message.answer(
        text="Action cancelled. Select a new action using the buttons below the keyboard.",
        reply_markup=main_actions_keyboard,
    )
    await state.clear()
