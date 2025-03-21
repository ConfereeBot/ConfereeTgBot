from enum import StrEnum


class Res(StrEnum):
    STARTED = "started"
    ERROR = "error"
    SUCCEDED = "succeded"
    BUSY = "busy"


class Req(StrEnum):
    SCREENSHOT = "screenshot"
    TIME = "time"


def prepare(res: Res, body, user_id=-1, filepath="") -> bytes:
    return str(
        {
            "type": res.value,
            "body": body,
            "user_id": user_id,
            "filepath": filepath,
        }
    ).encode()
