from datetime import datetime
from datetime import timezone as datetime_timezone

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from app.config import labels
from app.config.labels import CANCEL, REQUEST_TIME_PASSED, REQUEST_SCREENSHOT, REQUEST_STOP_RECORDING, BACK
from app.config.roles import Role
from app.database.db_operations.conference_db_operations import delete_conference_by_id
from app.database.db_operations.conference_db_operations import (
    get_conferences_by_tag,
    get_conference_by_link,
    get_conference_by_id,
)
from app.database.db_operations.recording_db_operations import get_recording_by_id
from app.database.db_operations.tag_db_operations import get_tag_by_id
from app.database.db_operations.user_db_operations import get_user_by_telegram_tag
from app.keyboards import (
    choose_recordings_search_method_keyboard as recordings_keyboard,
    inline_active_tag_list,
    inline_single_cancel_button,
    main_actions_keyboard,
)
from app.rabbitmq.func import decline_task, manage_active_task
from app.rabbitmq.responses import Req
from app.roles.admin.admin import admin
from app.roles.user.callbacks_enum import Callbacks
from app.roles.user.main_actions.recording_search.conference_status import ConferenceStatus
from app.roles.user.user_cmds import user
from app.utils.logger import logger


class RecordingSearchStates(StatesGroup):
    waiting_for_meet_link = State()
    browsing_conference = State()
    confirming_conference_deletion = State()
    requesting_screenshot = State()
    confirming_stop_recording = State()  # Новый статус для подтверждения остановки записи


@user.message(F.text == labels.GET_RECORD)
async def get_recording(message: Message):
    logger.info("get_recordings_call")
    await message.answer(
        text="Как вы хотите найти конференцию: по тегу или по ссылке?",
        reply_markup=recordings_keyboard,
    )


@user.callback_query(F.data == Callbacks.get_recording_by_tag_callback)
async def get_recording_by_tag(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.edit_text(
        text="Выберите тег конференции:",
        reply_markup=await inline_active_tag_list(
            on_item_clicked_callback=Callbacks.tag_clicked_in_search_mode_callback,
            on_cancel_clicked_callback=Callbacks.cancel_primary_action_callback,
            on_archived_clicked_callback=None,
            on_item_create_clicked_callback=None,
        ),
    )


@user.callback_query(F.data.startswith(Callbacks.tag_clicked_in_search_mode_callback))
async def process_tag_selection(callback: CallbackQuery, state: FSMContext):
    try:
        tag_id = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Ошибка: тег не выбран!", show_alert=True)
        return

    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден в базе данных!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    conferences = await get_conferences_by_tag(tag_id)
    if not conferences:
        await callback.message.edit_text(
            text=f"Конференций с тегом '{tag.name}' не найдено.",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    else:
        response = f"Найденные конференции с тегом '{tag.name}':\n\n"
        buttons = []
        for i, conference in enumerate(conferences, 1):
            if conference.next_meeting_timestamp is not None:
                timestamp_str = (datetime
                                 .fromtimestamp(conference.next_meeting_timestamp)
                                 .strftime(f'%d.%m.%Y %H:%M:%S UTC+{conference.timezone}'))
                print(conference.next_meeting_timestamp, int(datetime.now(datetime_timezone.utc).timestamp()))
                if conference.next_meeting_timestamp <= int(datetime.now(datetime_timezone.utc).timestamp()):
                    conference_status = ConferenceStatus.IN_PROGRESS
                else:
                    conference_status = ConferenceStatus.PLANNED
            else:
                conference_status = ConferenceStatus.FINISHED
                timestamp_str = "отсутствует, так как встреча не является регулярной."
            response += f"{i}. Конференция: {conference.link}\nДата: {timestamp_str}\nСтатус: {conference_status}\n\n"
            clean_link = conference.link.replace("https://", "").replace("http://", "").replace("www.", "")
            if conference.next_meeting_timestamp is not None:
                short_date = (datetime
                              .fromtimestamp(conference.next_meeting_timestamp)
                              .strftime('%d.%m.%Y %H:%M'))
            else:
                short_date = "не регулярная"
            button_text = f"{i}. {clean_link}, {short_date}"
            buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"open_conference:{conference.id}"
                )
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=CANCEL, callback_data=Callbacks.cancel_primary_action_callback)]
        )

        await callback.message.edit_text(
            text=response.strip(),
            reply_markup=keyboard,
        )
        await state.update_data(tag_id=tag_id)
    await callback.answer("")


@user.callback_query(F.data == Callbacks.get_recording_by_link_callback)
async def start_recording_by_link(callback: CallbackQuery, state: FSMContext):
    await callback.answer("")
    await callback.message.edit_text(
        text="Введите ссылку на Google Meet конференцию:",
        reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
    )
    await state.set_state(RecordingSearchStates.waiting_for_meet_link)


@user.message(RecordingSearchStates.waiting_for_meet_link)
async def process_meet_link(message: Message, state: FSMContext):
    meet_link = message.text.strip()
    telegram_tag = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    conference = await get_conference_by_link(meet_link)
    if conference:
        tag = await get_tag_by_id(str(conference.tag_id))
        if tag:
            if tag.is_archived:
                tag_name = tag.name + " (архивированный)"
            else:
                tag_name = tag.name
        else:
            tag_name = "Неизвестный тег"
        if conference.next_meeting_timestamp is not None:
            timestamp_str = (datetime
                             .fromtimestamp(conference.next_meeting_timestamp)
                             .strftime(f'%d.%m.%Y %H:%M:%S UTC+{conference.timezone}'))
            print(conference.next_meeting_timestamp, int(datetime.now(datetime_timezone.utc).timestamp()))
            if conference.next_meeting_timestamp <= int(datetime.now(datetime_timezone.utc).timestamp()):
                conference_status = ConferenceStatus.IN_PROGRESS
            else:
                conference_status = ConferenceStatus.PLANNED
        else:
            timestamp_str = "отсутствует, так как встреча не является регулярной."
            conference_status = ConferenceStatus.FINISHED
        if conference.recordings:
            response = f"Найдена конференция:\nСсылка: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}"
        else:
            response = f"Найдена конференция:\nСсылка: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}\n\nЗаписей пока нет."
        buttons = []
        current_time = int(datetime.now().timestamp())
        if conference.next_meeting_timestamp is not None and conference.next_meeting_timestamp <= current_time:
            buttons.extend([
                InlineKeyboardButton(
                    text=REQUEST_TIME_PASSED,
                    callback_data=f"duration:{conference.id}"
                ),
                InlineKeyboardButton(
                    text=REQUEST_SCREENSHOT,
                    callback_data=f"screenshot:{conference.id}"
                )
            ])
            if user.role >= Role.ADMIN:
                buttons.append(
                    InlineKeyboardButton(
                        text=REQUEST_STOP_RECORDING,
                        callback_data=f"stop_recording:{conference.id}"
                    )
                )
        if conference.recordings:
            for recording_id in conference.recordings:
                recording = await get_recording_by_id(str(recording_id))
                if recording:
                    recording_date = datetime.fromtimestamp(recording.timestamp).strftime('%d.%m.%Y %H:%M')
                    buttons.append(
                        InlineKeyboardButton(
                            text=f"Скачать запись {recording_date}",
                            url=recording.link
                        )
                    )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
        if user.role >= Role.ADMIN:
            keyboard.inline_keyboard.extend([
                [InlineKeyboardButton(text="🗑️ Удалить конференцию",
                                      callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
            ])
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=CANCEL, callback_data=Callbacks.cancel_primary_action_callback)]
        )
        await message.answer(
            text=response.strip(),
            reply_markup=keyboard,
        )
        await state.set_state(RecordingSearchStates.browsing_conference)
    else:
        await message.answer(
            text=f"Конференция с ссылкой '{meet_link}' не найдена, проверьте корректность ссылки.",
            reply_markup=main_actions_keyboard(user_role=user.role),
        )
    await state.clear()


@user.callback_query(F.data == Callbacks.cancel_primary_action_callback)
async def on_cancel_primary_callback(callback: CallbackQuery, state: FSMContext):
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    await callback.answer("")
    await callback.message.delete()
    await callback.message.answer(
        text="Действие отменено. Выберите новое действие с помощью кнопок под клавиатурой.",
        reply_markup=main_actions_keyboard(user.role),
    )
    await state.clear()


@user.callback_query(F.data.startswith("open_conference"))
async def handle_conference_button(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    tag = await get_tag_by_id(str(conference.tag_id))
    if tag:
        if tag.is_archived:
            tag_name = tag.name + " (архивированный)"
        else:
            tag_name = tag.name
    else:
        tag_name = "Неизвестный тег"
    if conference.next_meeting_timestamp is not None:
        timestamp_str = (datetime
                         .fromtimestamp(conference.next_meeting_timestamp)
                         .strftime(f'%d.%m.%Y %H:%M:%S UTC+{conference.timezone}'))
        print(conference.next_meeting_timestamp, int(datetime.now(datetime_timezone.utc).timestamp()))
        if conference.next_meeting_timestamp <= int(datetime.now(datetime_timezone.utc).timestamp()):
            conference_status = ConferenceStatus.IN_PROGRESS
        else:
            conference_status = ConferenceStatus.PLANNED
    else:
        timestamp_str = "отсутствует, так как встреча не является регулярной."
        conference_status = ConferenceStatus.FINISHED
    if conference.recordings:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}"
    else:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}\n\nЗаписей пока нет."
    buttons = []
    current_time = int(datetime.now().timestamp())
    if conference.next_meeting_timestamp is not None and conference.next_meeting_timestamp <= current_time:
        buttons.extend([
            InlineKeyboardButton(
                text=REQUEST_TIME_PASSED,
                callback_data=f"duration:{conference.id}"
            ),
            InlineKeyboardButton(
                text=REQUEST_SCREENSHOT,
                callback_data=f"screenshot:{conference.id}"
            )
        ])
        if user.role >= Role.ADMIN:
            buttons.append(
                InlineKeyboardButton(
                    text=REQUEST_STOP_RECORDING,
                    callback_data=f"stop_recording:{conference.id}"
                )
            )
    if conference.recordings:
        for recording_id in conference.recordings:
            recording = await get_recording_by_id(str(recording_id))
            if recording:
                recording_date = datetime.fromtimestamp(recording.timestamp).strftime('%d.%m.%Y %H:%M')
                buttons.append(
                    InlineKeyboardButton(
                        text=f"Скачать запись {recording_date}",
                        url=recording.link
                    )
                )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
    if user.role >= Role.ADMIN:
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="🗑️ Удалить конференцию",
                                  callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
        ])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=BACK,
                              callback_data=f"{Callbacks.back_to_tag_in_search_mode}:{conference.tag_id}")]
    )

    await callback.message.edit_text(
        text=response.strip(),
        reply_markup=keyboard,
    )
    await state.set_state(RecordingSearchStates.browsing_conference)
    await callback.answer("")


@user.callback_query(F.data.startswith("screenshot"))
async def handle_screenshot_request(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    await state.update_data(conference_id=conference_id)
    response = "Эта функция позволяет получить скриншот встречи и узнать, что происходит в конференции прямо сейчас."
    current_time = int(datetime.now().timestamp())

    if conference.next_meeting_timestamp is not None and conference.next_meeting_timestamp <= current_time:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Запросить скриншот",
                                  callback_data=f"request_screenshot:{conference_id}")],
            [InlineKeyboardButton(text="↩ Назад",
                                  callback_data=f"back_to_conference:{conference_id}")]
        ])
    else:
        await callback.answer(
            "Конференция ещё не началась, скриншот не может быть запрошен!",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        text=response,
        reply_markup=keyboard
    )
    await state.set_state(RecordingSearchStates.requesting_screenshot)
    await callback.answer("")


@user.callback_query(F.data.startswith("request_screenshot"))
async def process_screenshot_request(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    await callback.message.delete()
    await manage_active_task(command=Req.SCREENSHOT, user_id=user.telegram_id)
    await callback.message.answer(
        text="Скриншот запрошен! Он будет отправлен, как только готов.",
        reply_markup=main_actions_keyboard(user.role)
    )
    await state.clear()
    await callback.answer("")


@user.callback_query(F.data.startswith("duration"))
async def handle_duration_request(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    await callback.message.delete()
    await manage_active_task(command=Req.TIME, user_id=user.telegram_id)
    await callback.message.answer(
        text="Запрос о времени записи конференции отправлен! Бот даст знать, когда придёт ответ.",
        reply_markup=main_actions_keyboard(user.role)
    )
    await state.clear()
    await callback.answer("")


@user.callback_query(F.data.startswith("stop_recording"))
async def handle_stop_recording_request(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user or user.role < Role.ADMIN:
        await callback.answer("У вас нет прав для остановки записи!", show_alert=True)
        return

    await state.update_data(conference_id=conference_id)
    await callback.message.edit_text(
        text=f"Вы уверены, что хотите остановить запись конференции?\nСсылка: {conference.link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩ Назад",
                                  callback_data=f"back_to_conference:{conference_id}")],
            [InlineKeyboardButton(text="Подтвердить",
                                  callback_data=f"confirm_stop_recording:{conference_id}")]
        ])
    )
    await state.set_state(RecordingSearchStates.confirming_stop_recording)
    await callback.answer("")


@user.callback_query(F.data.startswith("confirm_stop_recording"))
async def confirm_stop_recording(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user or user.role < Role.ADMIN:
        await callback.answer("У вас нет прав для остановки записи!", show_alert=True)
        return

    await callback.message.delete()
    await manage_active_task(command=Req.STOP_RECORD, user_id=user.telegram_id)
    await callback.message.answer(
        text="Запрос на завершение записи был отправлен. Вы получите уведомление о конце записи, если бот одобрит ваш запрос.",
        reply_markup=main_actions_keyboard(user.role)
    )
    await state.clear()
    await callback.answer("")


@user.callback_query(F.data.startswith("back_to_conference"))
async def back_to_conference(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    tag = await get_tag_by_id(str(conference.tag_id))
    if tag:
        if tag.is_archived:
            tag_name = tag.name + " (архивированный)"
        else:
            tag_name = tag.name
    else:
        tag_name = "Неизвестный тег"
    if conference.next_meeting_timestamp is not None:
        timestamp_str = (datetime
                         .fromtimestamp(conference.next_meeting_timestamp)
                         .strftime(f'%d.%m.%Y %H:%M:%S UTC+{conference.timezone}'))
        print(conference.next_meeting_timestamp, int(datetime.now(datetime_timezone.utc).timestamp()))
        if conference.next_meeting_timestamp <= int(datetime.now(datetime_timezone.utc).timestamp()):
            conference_status = ConferenceStatus.IN_PROGRESS
        else:
            conference_status = ConferenceStatus.PLANNED
    else:
        timestamp_str = "отсутствует, так как встреча не является регулярной."
        conference_status = ConferenceStatus.FINISHED
    if conference.recordings:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}"
    else:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}\n\nЗаписей пока нет."
    buttons = []
    current_time = int(datetime.now().timestamp())
    if conference.next_meeting_timestamp is not None and conference.next_meeting_timestamp <= current_time:
        buttons.extend([
            InlineKeyboardButton(
                text=REQUEST_TIME_PASSED,
                callback_data=f"duration:{conference.id}"
            ),
            InlineKeyboardButton(
                text=REQUEST_SCREENSHOT,
                callback_data=f"screenshot:{conference.id}"
            )
        ])
        if user.role >= Role.ADMIN:
            buttons.append(
                InlineKeyboardButton(
                    text=REQUEST_STOP_RECORDING,
                    callback_data=f"stop_recording:{conference.id}"
                )
            )
    if conference.recordings:
        for recording_id in conference.recordings:
            recording = await get_recording_by_id(str(recording_id))
            if recording:
                recording_date = datetime.fromtimestamp(recording.timestamp).strftime('%d.%m.%Y %H:%M')
                buttons.append(
                    InlineKeyboardButton(
                        text=f"Скачать запись {recording_date}",
                        url=recording.link
                    )
                )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
    if user.role >= Role.ADMIN:
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="🗑️ Удалить конференцию",
                                  callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
        ])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=BACK,
                              callback_data=f"{Callbacks.back_to_tag_in_search_mode}:{conference.tag_id}")]
    )

    await callback.message.edit_text(
        text=response.strip(),
        reply_markup=keyboard,
    )
    await state.set_state(RecordingSearchStates.browsing_conference)
    await callback.answer("")


@user.callback_query(F.data.startswith(Callbacks.back_to_tag_in_search_mode))
async def handle_back_to_tag_in_search_mode(callback: CallbackQuery, state: FSMContext):
    tag_id = callback.data.split(":")[1]
    tag = await get_tag_by_id(tag_id)
    if not tag:
        await callback.answer("Ошибка: тег не найден!", show_alert=True)
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    conferences = await get_conferences_by_tag(tag_id)
    if not conferences:
        await callback.message.edit_text(
            text=f"Конференций с тегом '{tag.name}' не найдено.",
            reply_markup=await inline_single_cancel_button(Callbacks.cancel_primary_action_callback),
        )
    else:
        response = f"Найденные конференции с тегом '{tag.name}':\n\n"
        buttons = []
        for i, conference in enumerate(conferences, 1):
            if conference.next_meeting_timestamp is not None:
                timestamp_str = (datetime
                                 .fromtimestamp(conference.next_meeting_timestamp)
                                 .strftime(f'%d.%m.%Y %H:%M:%S UTC+{conference.timezone}'))
                print(conference.next_meeting_timestamp, int(datetime.now(datetime_timezone.utc).timestamp()))
                if conference.next_meeting_timestamp <= int(datetime.now(datetime_timezone.utc).timestamp()):
                    conference_status = ConferenceStatus.IN_PROGRESS
                else:
                    conference_status = ConferenceStatus.PLANNED
            else:
                timestamp_str = "отсутствует, так как встреча не является регулярной."
                conference_status = ConferenceStatus.FINISHED
            response += f"{i}. Конференция: {conference.link}\nДата: {timestamp_str}\nСтатус: {conference_status}\n\n"
            clean_link = conference.link.replace("https://", "").replace("http://", "").replace("www.", "")
            if conference.next_meeting_timestamp is not None:
                short_date = (datetime
                              .fromtimestamp(conference.next_meeting_timestamp)
                              .strftime('%d.%m.%Y %H:%M'))
            else:
                short_date = "не регулярная"
            button_text = f"{i}. {clean_link}, {short_date}"
            buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"open_conference:{conference.id}"
                )
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=CANCEL, callback_data=Callbacks.cancel_primary_action_callback)]
        )

        await callback.message.edit_text(
            text=response.strip(),
            reply_markup=keyboard,
        )
    await state.clear()
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.delete_conference_callback))
async def handle_delete_conference(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        return

    await state.update_data(conference_id=conference_id)
    await callback.message.edit_text(
        text=f"❗ Требуется подтверждение опасного действия\n\nВы уверены, что хотите удалить конференцию и все связанные с ней записи?\nСсылка: {conference.link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩ Отменить",
                                  callback_data=f"{Callbacks.cancel_delete_conference}:{conference_id}"),
             InlineKeyboardButton(text="Подтвердить",
                                  callback_data=f"{Callbacks.confirm_delete_conference}:{conference_id}")
             ],
        ]),
    )
    await state.set_state(RecordingSearchStates.confirming_conference_deletion)
    await callback.answer("")


@admin.callback_query(F.data.startswith(Callbacks.confirm_delete_conference))
async def confirm_delete_conference(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    logger.info(f"Got conference id {conference_id} in confirmation callback")
    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return
    conference = await get_conference_by_id(conference_id)
    if conference is None:
        logger.info(f"Error while searching for {conference_id} in db, no such conference.")
        await callback.answer("Error")
        return
    success, response = await delete_conference_by_id(conference_id)
    logger.info(f"delete_conference_by_id result: success={success}, response: {response}")
    if success:
        await decline_task(conference.link)
        await callback.message.delete()
        await callback.message.answer(
            text=response,
            reply_markup=main_actions_keyboard(user.role),
        )
    else:
        await callback.message.answer(
            text=response,
            reply_markup=main_actions_keyboard(user.role),
        )
    await state.clear()
    await callback.answer("")
    logger.info("Finished confirm_delete_conference function")


@admin.callback_query(F.data.startswith(Callbacks.cancel_delete_conference))
async def cancel_delete_conference(callback: CallbackQuery, state: FSMContext):
    conference_id = callback.data.split(":")[1]
    conference = await get_conference_by_id(conference_id)
    if not conference:
        await callback.answer("Ошибка: конференция не найдена!", show_alert=True)
        await state.clear()
        return

    telegram_tag = f"@{callback.from_user.username}" if callback.from_user.username else f"@{callback.from_user.id}"
    user = await get_user_by_telegram_tag(telegram_tag)
    if not user:
        return

    tag = await get_tag_by_id(str(conference.tag_id))
    if tag:
        if tag.is_archived:
            tag_name = tag.name + " (архивированный)"
        else:
            tag_name = tag.name
    else:
        tag_name = "Неизвестный тег"
    if conference.next_meeting_timestamp is not None:
        timestamp_str = (datetime
                         .fromtimestamp(conference.next_meeting_timestamp)
                         .strftime(f'%d.%m.%Y %H:%M:%S UTC+{conference.timezone}'))
        print(conference.next_meeting_timestamp, int(datetime.now(datetime_timezone.utc).timestamp()))
        if conference.next_meeting_timestamp <= int(datetime.now(datetime_timezone.utc).timestamp()):
            conference_status = ConferenceStatus.IN_PROGRESS
        else:
            conference_status = ConferenceStatus.PLANNED
    else:
        timestamp_str = "отсутствует, так как встреча не является регулярной."
        conference_status = ConferenceStatus.FINISHED
    if conference.recordings:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}"
    else:
        response = f"Конференция: {conference.link}\nТег: {tag_name}\nСтатус: {conference_status}\nДата следующей встречи: {timestamp_str}\n\nЗаписей пока нет."
    buttons = []
    current_time = int(datetime.now().timestamp())
    if conference.next_meeting_timestamp is not None and conference.next_meeting_timestamp <= current_time:
        buttons.extend([
            InlineKeyboardButton(
                text=REQUEST_TIME_PASSED,
                callback_data=f"duration:{conference.id}"
            ),
            InlineKeyboardButton(
                text=REQUEST_SCREENSHOT,
                callback_data=f"screenshot:{conference.id}"
            )
        ])
        if user.role >= Role.ADMIN:
            buttons.append(
                InlineKeyboardButton(
                    text=REQUEST_STOP_RECORDING,
                    callback_data=f"stop_recording:{conference.id}"
                )
            )
    if conference.recordings:
        for recording_id in conference.recordings:
            recording = await get_recording_by_id(str(recording_id))
            if recording:
                recording_date = datetime.fromtimestamp(recording.timestamp).strftime('%d.%m.%Y %H:%M')
                buttons.append(
                    InlineKeyboardButton(
                        text=f"Скачать запись {recording_date}",
                        url=recording.link
                    )
                )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
    if user.role >= Role.ADMIN:
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="🗑️ Удалить конференцию",
                                  callback_data=f"{Callbacks.delete_conference_callback}:{conference.id}")],
        ])
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text=BACK,
                              callback_data=f"{Callbacks.back_to_tag_in_search_mode}:{conference.tag_id}")]
    )

    await callback.message.edit_text(
        text=response.strip(),
        reply_markup=keyboard,
    )
    await state.set_state(RecordingSearchStates.browsing_conference)
    await callback.answer("")
