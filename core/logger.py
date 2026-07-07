import logging
import sys
from core.config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Factory function to configure and return a standardized logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if the logger has already been configured
    if not logger.handlers:
        logger.setLevel(settings.log_level.upper())

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H-%M-%S"
        )

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger

# The process can be simplified with `loguru` defined in each place you want to log
# from loguru import logger
# import sys

# logger.remove()

# logger.add(
#     sys.stdout,
#     format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} | {message}",
#     level="INFO"
# )

# logger.info("Connected successfully")
