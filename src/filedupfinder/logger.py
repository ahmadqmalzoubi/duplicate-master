import logging


def setup_logger(args):
    logger = logging.getLogger("duplicate_finder")
    logger.setLevel(getattr(logging, args.loglevel.upper()))
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)

    if args.logfile:
        file_handler = logging.FileHandler(args.logfile)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)

    return logger
