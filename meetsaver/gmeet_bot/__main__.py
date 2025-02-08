import nodriver as uc

from .. import utils
from .gmeet import GMeet

logger = utils.logger.setup_logger(__name__)


async def main():
    link = await GMeet().record_meet("https://meet.google.com/vua-utey-jow")
    logger.info(link)


if __name__ == "__main__":
    logger.info("Starting gmeet recorder...")
    uc.loop().run_until_complete(main())
    logger.info("Finished gmeet recording.")
