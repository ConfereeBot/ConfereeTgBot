import asyncio

from .. import utils
from .gmeet import record_meet

logger = utils.logger.setup_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting gmeet recorder...")
    asyncio.run(record_meet("https://meet.google.com/wsc-ywte-njv"))
    logger.info("Finished gmeet recording.")
