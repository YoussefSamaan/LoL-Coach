import logging
import sys
from app.utils.logger import get_logger

def test_get_logger_creation():
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream == sys.stdout

def test_get_logger_singleton_behavior():
    # Calling it twice should not add multiple handlers
    logger1 = get_logger("repeat_logger")
    logger2 = get_logger("repeat_logger")
    
    assert logger1 is logger2
    assert len(logger1.handlers) == 1

def test_logger_formatter():
    logger = get_logger("formatted_logger")
    handler = logger.handlers[0]
    formatter = handler.formatter
    # Check format string presence
    # "%(asctime)s | [%(levelname)s] | %(name)s | %(message)s"
    assert "%(asctime)s" in formatter._fmt
    assert "%(levelname)s" in formatter._fmt
    assert "%(name)s" in formatter._fmt
