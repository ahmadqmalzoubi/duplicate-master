import logging
import sys


def setup_logger(args):
    logger = logging.getLogger("filedupfinder")
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
