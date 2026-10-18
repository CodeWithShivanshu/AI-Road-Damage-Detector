"""
RoadVision AI - Structured Logging Module
Provides standardized logging with formatting and level control.
"""

import logging
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

FORMATTER = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str = "roadvision") -> logging.Logger:
    """Returns a pre-configured logger with console output handler."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    if not logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(FORMATTER)
        logger.addHandler(ch)
        logger.propagate = False

    return logger
