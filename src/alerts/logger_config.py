"""Logging configuration for the NFCC platform."""

import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """Configure logging for the application."""
    if level is None:
        import os

        level = os.getenv("LOG_LEVEL", "INFO")

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger("nfcc")
    logger.info(f"Logging initialized at level: {level}")
