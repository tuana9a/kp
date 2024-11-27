import os
from datetime import datetime


def now():
    current = datetime.now()
    formatted = current.strftime("%Y-%m-%d %H:%M:%S")
    return formatted


class Logger:

    def __init__(self):
        pass

    def error(self, *msg):
        pass

    def warn(self, *msg):
        pass

    def info(self, *msg):
        pass

    def debug(self, *msg):
        pass


class ErrorLogger(Logger):

    def error(self, *msg):
        print(f"{now()} [ERROR] {msg}")


class WarnLogger(ErrorLogger):

    def warn(self, *msg):
        print(f"{now()} [WARM] {msg}")


class InfoLogger(WarnLogger):

    def info(self, *msg):
        print(f"{now()} [INFO] {msg}")


class DebugLogger(InfoLogger):

    def debug(self, *msg):
        print(f"{now()} [DEBUG] {msg}")


def from_env():
    level = (os.getenv("LOGGER") or "").upper()
    if level == "DEBUG":
        return DebugLogger()
    if level == "INFO":
        return InfoLogger()
    if level == "WARN":
        return WarnLogger()
    return ErrorLogger()
