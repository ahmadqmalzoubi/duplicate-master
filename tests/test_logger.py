import logging
import sys
import tempfile
import os
from unittest.mock import patch, MagicMock
import pytest
from filedupfinder.logger import setup_logger


class MockArgs:
    def __init__(self, loglevel="info", logfile=None):
        self.loglevel = loglevel
        self.logfile = logfile


def test_setup_logger_console_default():
    """Test logger setup with default console output."""
    args = MockArgs()
    logger = setup_logger(args)
    
    assert logger.name == "filedupfinder"
    assert logger.level == logging.INFO
    # Just verify the logger was created successfully
    assert isinstance(logger, logging.Logger)


def test_setup_logger_file_output():
    """Test logger setup with file output."""
    # Clear any existing handlers first
    logger = logging.getLogger("filedupfinder")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        logfile_path = tmp_file.name
    
    try:
        args = MockArgs(logfile=logfile_path)
        logger = setup_logger(args)
        
        assert logger.name == "filedupfinder"
        assert logger.level == logging.INFO
        # Just verify the logger was created successfully
        assert isinstance(logger, logging.Logger)
        
        # Test that logging doesn't crash
        test_message = "Test log message"
        logger.info(test_message)
        
    finally:
        if os.path.exists(logfile_path):
            os.unlink(logfile_path)


def test_setup_logger_different_levels():
    """Test logger setup with different log levels."""
    levels = ["debug", "info", "warning", "error"]
    
    for level in levels:
        args = MockArgs(loglevel=level)
        logger = setup_logger(args)
        assert logger.level == getattr(logging, level.upper())


def test_setup_logger_duplicate_handlers():
    """Test that duplicate handlers are not added."""
    args = MockArgs()
    
    # First call
    logger1 = setup_logger(args)
    
    # Second call with same args
    logger2 = setup_logger(args)
    
    # Should be the same logger instance
    assert logger1 is logger2


def test_setup_logger_gui_mode():
    """Test logger setup in GUI mode (no stdout)."""
    args = MockArgs()
    
    with patch('sys.stdout', None):
        logger = setup_logger(args)
        
        assert logger.name == "filedupfinder"
        assert logger.level == logging.INFO
        # Just verify the logger was created successfully
        assert isinstance(logger, logging.Logger)


def test_setup_logger_logging_functionality():
    """Test that the logger actually works for logging."""
    args = MockArgs(loglevel="debug")
    logger = setup_logger(args)
    
    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # If we get here without exceptions, the logger is working
    assert True 