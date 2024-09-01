
import logging
import traceback
from enum import Enum
from inspect import stack

from django.utils import timezone


class LogType(Enum):
    info = "Info"
    debug = "Debug"
    warning = "Warning"
    error = "Error"
    critical = "Critical"
    fatal = "Fatal"


class AppLogger:

    @staticmethod
    def debug(msg, *args, **kwargs):
        get_logger(stack()).debug(msg, *args, **kwargs)

    @staticmethod
    def info(msg, *args, **kwargs):
        get_logger(stack()).info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg, *args, **kwargs):
        get_logger(stack()).warning(msg, *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        get_logger(stack()).error(msg, *args, **kwargs)

    @staticmethod
    def exception(msg, *args, **kwargs):
        get_logger(stack()).exception(msg, *args, exc_info=True, **kwargs)

    @staticmethod
    def critical(msg, *args, **kwargs):
        get_logger(stack()).critical(msg, *args, exc_info=True, **kwargs)

    @staticmethod
    def fatal(msg, *args, **kwargs):
        get_logger(stack()).fatal(msg, *args, exc_info=True, **kwargs)

    @staticmethod
    def log(msg, *args, **kwargs):
        AppLogger.print(*args)

    @staticmethod
    def print(*args, log_type=LogType.debug):
        print("{}::[{}]".format(log_type, timezone.now()), *args)

    @staticmethod
    def report(e=None, error=None):
        if e:
            traceback.print_exc()

        if error:
            AppLogger.print(error, log_type=LogType.error)



def get_logger(s):
    return logging.getLogger(s[1].filename)
