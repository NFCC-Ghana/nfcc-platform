"""Centralized logging configuration for NFCC alerts."""

import logging
import sys


def setup_logging(level=logging.INFO):
    """Configure logging for all alert modules."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Set up specific loggers
    for name in [
        "nfcc.alert.engine",
        "nfcc.alert.mock",
        "nfcc.alert.whatsapp",
        "nfcc.alert.sms",
        "nfcc.alert.email",
        "nfcc.scheduler",
    ]:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)

    return root_logger
