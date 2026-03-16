import logging
from pythonjsonlogger import jsonlogger


def configure_logging(level: str) -> None:
    logger = logging.getLogger()
    logger.setLevel(level)

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)

    logger.handlers = [handler]
