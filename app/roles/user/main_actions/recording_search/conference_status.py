from enum import StrEnum


class ConferenceStatus(StrEnum):
    PLANNED = "запланирована 🗓️"
    IN_PROGRESS = "записывается 🎥"
    FINISHED = "завершилась 🏁"
