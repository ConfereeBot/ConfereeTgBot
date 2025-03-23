from . import func, responses

__all__ = ["responses", "func"]

""" USAGE

Всё обрабатывай в mq.func.handle_responses, там я написал # TODO для твоего кода

await mq.func.schedule_task("https://meet.google.com/qwe-qwe-qwe", 0)           schedule task in n secs
await mq.func.manage_active_task(mq.responses.Req.TIME, user_id: int)           request for current recording time
await mq.func.manage_active_task(mq.responses.Req.SCREENSHOT, user_id: int)     request for screenshot
await mq.func.manage_active_task(mq.responses.Req.STOP_RECORD, user_id: int)    request for stop recording
await mq.func.decline_task("https://meet.google.com/qwe-qwe-qwe")               delete task from schedule
"""
