import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Standardizes logger configuration across the application.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler(sys.stdout)

        # Simple, readable format
        formatter = logging.Formatter(
            "%(asctime)s | [%(levelname)s] | %(name)s | %(message)s", datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
