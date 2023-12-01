import logging
from logging.handlers import RotatingFileHandler
import sys
from logging import FileHandler, StreamHandler
from os import PathLike
from typing import Union


class Logger:
    """Logging class that logs Warnings to stderr and Info to file.

    Parameters
    ----------
    logger_name : str
        Internal name of logger.

    """

    def __init__(self, logger_name: str, logger_path: Union[str, PathLike] = None):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # output to stderr as to allow clean piping of output
        console_handler = StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)

        # file_handler = FileHandler(f'./{logger_name}.log')
        # file_handler.setLevel(logging.INFO)
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        # file_handler.setFormatter(formatter)
        console_handler.setFormatter(self.formatter)

        logger.addHandler(console_handler)
        # logger.addHandler(file_handler)
        self.logger = logger

    def _add_file_handler(self, logger_path: Union[str, PathLike] = None):
        if logger_path is None:
            logger_path = f"./{self.logger_name}.log"

        file_handler = RotatingFileHandler(logger_path, maxBytes=1e6, backupCount=3)
        file_handler.setLevel(logging.INFO)

        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
        self.start_run()

    def start_run(self) -> None:
        """Prints a line in the logs signifying a new run."""

        self.logger.info("======== New run =========")

    def setLevel(self, loglevel):
        if self.logger.handlers:
            for handler in self.logger.handlers:
                handler.setLevel(loglevel)
        else:
            logging.basicConfig(level=loglevel)
