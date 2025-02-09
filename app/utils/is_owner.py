import os

owner_ids = os.getenv("OWNERS", "").split(",")


def is_owner(tg_id: str) -> bool:
    return tg_id.strip() in owner_ids
