import logging
import os
from logging.handlers import RotatingFileHandler

log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)
log_filepath = os.path.join(log_dir, "meetsaver.log")


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

    return logger
