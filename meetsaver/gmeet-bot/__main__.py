import nodriver as uc

from .. import utils
from .gmeet import record_meet

logger = utils.logger.setup_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting gmeet recorder...")
    uc.loop().run_until_complete(record_meet("https://meet.google.com/qxx-bddb-cnt"))
    logger.info("Finished gmeet recording.")
