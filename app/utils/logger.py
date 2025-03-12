import logging
import os
from logging.handlers import RotatingFileHandler

log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)
log_filepath = os.path.join(log_dir, "conferee_tg_bot.log")


def setup_logger(logger_name):
    """Настройка логгеров.

    Returns:
        Logger: Логгер.
    """

    if len(logging.getLogger().handlers) > 0:
        return logging.getLogger(logger_name)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                log_filepath,
                maxBytes=10 * 1024 * 1024,
                backupCount=10,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )

    # Custom
    logger = logging.getLogger(logger_name)

    # Ignore Mongo's debug messages
    logging.getLogger("pymongo.topology").setLevel(logging.INFO)

    return logger
