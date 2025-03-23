import os
from typing import List

# Получаем базовые переменные из окружения
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "conferee_db")
MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb")  # mongodb для Docker, localhost для локальной разработки

# Проверяем, что обязательные переменные заданы
if not MONGODB_USERNAME or not MONGODB_PASSWORD:
    raise ValueError("MONGODB_USERNAME and MONGODB_PASSWORD must be set in environment variables!")


MONGODB_URI = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_HOST}:27017/{MONGODB_DATABASE}?authSource=admin"

OWNERS: List[str] = os.getenv("OWNERS", "").split(",") if os.getenv("OWNERS") else []
OWNERS = [owner.strip() for owner in OWNERS if owner.strip()]
