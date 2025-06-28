import logging
import sys
from typing import Any


def setup_logger(args: Any) -> logging.Logger:
    """
    Set up and configure the application logger.

    This function creates and configures a logger instance for the duplicate file finder
    application. It supports both file and console output, with configurable log levels
    and proper formatting. The logger is designed to work in both CLI and GUI environments.

    Args:
        args: Command-line arguments object containing loglevel and logfile settings.
              Expected attributes:
              - loglevel: String representing the log level (debug, info, warning, error)
              - logfile: Optional path to log file (if None, logs to console)

    Returns:
        logging.Logger: Configured logger instance ready for use.

    Examples:
        >>> args = type('Args', (), {'loglevel': 'info', 'logfile': None})()
        >>> logger = setup_logger(args)
        >>> logger.info("Application started")
        [INFO]    Application started

        >>> args = type('Args', (), {'loglevel': 'debug', 'logfile': 'app.log'})()
        >>> logger = setup_logger(args)
        >>> logger.debug("Debug information")
        # Writes to app.log file

    Note:
        - If logfile is specified, logs are written to the file
        - If no logfile and no stdout (GUI mode), uses NullHandler
        - Log format: [LEVEL]    message
        - Prevents duplicate handlers if called multiple times
    """
    logger = logging.getLogger("duplicatemaster")
    logger.setLevel(logging.getLevelName(args.loglevel.upper()))

    # Avoid duplicate handlers
    if logger.hasHandlers():
        return logger

    if args.logfile:
        handler = logging.FileHandler(args.logfile)
    else:
        # Fix for GUI app: fallback to NullHandler if no stdout
        if sys.stdout is None:
            handler = logging.NullHandler()
        else:
            handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('[%(levelname)s]    %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
