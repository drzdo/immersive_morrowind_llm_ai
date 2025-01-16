import logging
import logging.handlers
import os
from typing import Any, Literal, Union
import contextvars

import colorlog
from pydantic import BaseModel


class Logger:
    class Config(BaseModel):
        log_to_console: bool
        log_to_console_level: Union[Literal['info'], Literal['debug']]

        log_to_file: bool
        log_to_file_level: Union[Literal['info'], Literal['debug']]

    _ctx = contextvars.ContextVar[str]('logctx', default='default')

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def debug(self, msg: Any):
        # self._logger.debug(msg, extra={"ctx": Logger._ctx.get("undefined") or "undefined"})
        self._logger.debug(msg)

    def info(self, msg: Any):
        # self._logger.info(msg, extra={"ctx": Logger._ctx.get("undefined") or "undefined"})
        self._logger.info(msg)

    def warning(self, msg: Any):
        # self._logger.warning(msg, extra={"ctx": Logger._ctx.get("undefined") or "undefined"})
        self._logger.warning(msg)

    def error(self, msg: Any):
        # self._logger.error(msg, extra={"ctx": Logger._ctx.get("undefined") or "undefined"})
        self._logger.error(msg)

    def critical(self, msg: Any):
        # self._logger.critical(msg, extra={"ctx": Logger._ctx.get("undefined") or "undefined"})
        self._logger.critical(msg)

    @staticmethod
    def set_ctx(value: str):
        Logger._ctx.set(value)

    @staticmethod
    def setup_logs(config: Config):
        def get_log_level(value: str) -> int:
            return logging.getLevelNamesMapping()[value.upper()]

        if config.log_to_console:
            h = colorlog.StreamHandler()
            h.setFormatter(colorlog.ColoredFormatter(
                # '%(log_color)s%(asctime)s %(blue)s%(name)s[%(process)d] %(white)s(%(ctx)s) %(log_color)s%(levelname)s %(white)s%(message)s',
                '%(log_color)s%(asctime)s %(blue)s%(name)s[%(process)d] %(log_color)s%(levelname)s %(white)s%(message)s',
                log_colors={
                    "DEBUG": "purple",
                    "INFO": "cyan",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                }
            ))
            h.setLevel(get_log_level(config.log_to_console_level))
            logging.getLogger().addHandler(h)

        if config.log_to_file:
            erase: list[str] = [
                "\033[0;32m",
                "\033[0m",
                "\033[1;33m",
                "\033[0;31m"
            ]

            class Formatter(logging.Formatter):
                def formatMessage(self, record: logging.LogRecord) -> str:
                    for s in erase:
                        record.message = record.message.replace(s, "")
                    return super().formatMessage(record)

            log_exists = os.path.exists("rpgaiserver.log")
            h = logging.handlers.RotatingFileHandler("rpgaiserver.log", "a", encoding='utf-8', backupCount=3)
            if log_exists:
                h.doRollover()
            h.setFormatter(Formatter(
                # '%(asctime)s %(name)s[%(process)d] (%(ctx)s) %(levelname)s %(message)s'
                '%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s'
            ))
            h.setLevel(get_log_level(config.log_to_file_level))
            logging.getLogger().addHandler(h)

        min_log_level = min(
            get_log_level(config.log_to_file_level),
            get_log_level(config.log_to_console_level)
        )
        logging.basicConfig(level=min_log_level)
        logging.getLogger().setLevel(min_log_level)
