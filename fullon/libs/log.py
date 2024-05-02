"""
Setting to log
"""
import logging
from os import mkdir
from libs import settings
from colorlog import ColoredFormatter


class LogFilter():
    """
    Filter logs by level type
    """

    def __init__(self, level):
        """Constructor"""
        self.__level = level

    def filter(self, log_record):
        """
        Filters logRecord by level
        """
        return log_record.levelno <= self.__level


def fullon_logger(name: str) -> logging.Logger:
    """
    Configures a fullon logger with colorized output
    """
    try:
        console = settings.CONSOLE_LOG
    except AttributeError:
        console = False
    try:
        filename = settings.LOG_FILE
    except AttributeError:
        filename = False
    try:
        match settings.LOG_LEVEL:
            case "logging.ERROR":
                log_level = logging.ERROR
            case "logging.WARNING":
                log_level = logging.WARNING
            case "logging.INFO":
                log_level = logging.INFO
            case "logging.DEBUG":
                log_level = logging.DEBUG
            case _:
                log_level = logging.ERROR
    except AttributeError:
        log_level = logging.ERROR

    # Setup the colorized formatter
    color_formatter = ColoredFormatter(
        '%(log_color)s%(asctime)s - %(levelname)s - %(module)s (L: %(lineno)d) - %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'white',
            'WARNING': 'light_yellow',
            'ERROR': 'light_red',
            'CRITICAL': 'light_red'
        }
    )

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    if logger.hasHandlers():
        logger.handlers.clear()

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(color_formatter)
        logger.addHandler(stream_handler)

    if filename:
        try:
            file_handler = logging.FileHandler(filename)
        except FileNotFoundError:
            logger.error("Can't find log file %s", filename)
            logger.error("Attempting to create")
            dirname = '/'.join(filename.split("/")[:-1])
            mkdir(dirname)
            file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(color_formatter)
        logger.addHandler(file_handler)

    return logger


def setup_custom_logger_no_settings(name, log_level=10):
    """_summary_

    Args:
        name (_type_): _description_
        log_level (int, optional): _description_. Defaults to 10.

    Returns:
        _type_: _description_
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    return logger


def secret_logger() -> logging.getLogger:
    """
    Logger for Google Secret Manager, needs to filter error messages
    as they appear always with use of .json file
    """
    logger = logging.getLogger('secret_manager')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(lineno)d - %(levelname)s - %(module)s - %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(LogFilter(logging.INFO))
    logger.addHandler(stream_handler)
    return logger


def default_log() -> logging.getLogger:
    """
    Returns the default logger for Fullon

    Returns:
        logging.getLogger: a configured logger
    """
    return setup_custom_logger_no_settings(name="General Log Fullon")