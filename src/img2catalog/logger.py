import logging
import sys
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from os import PathLike
from typing import Union

LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGGING_DATEFMT = "%Y-%m-%d %H:%M:%S"


class Logger:
    """Logging class that logs Warnings to stderr and Info to file.

    Parameters
    ----------
    logger_name : str
        Internal name of logger.
    logger_path : str, PathLike
        Path to the logfile

    """

    def __init__(self, logger_name: str, logger_path: Union[str, PathLike] = None) -> None:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # output to stderr as to allow clean piping of output
        console_handler = StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)

        self.formatter = logging.Formatter(LOGGING_FORMAT, datefmt=LOGGING_DATEFMT)
        console_handler.setFormatter(self.formatter)

        logger.addHandler(console_handler)
        self.logger_name = logger_name
        self.logger = logger
        self.logger_path = logger_path
        if self.logger_path is None:
            self.logger_path = f"./{self.logger_name}.log"

    def _add_file_handler(self, logger_path: Union[str, PathLike] = None) -> None:
        """Adds a file handler to logging

        Parameters
        ----------
        logger_path : Union[str, PathLike], optional
            Location to store logfile. If not set, will use self.logger_path, if that isn't set
            either, a logfile with the name of the logger will be stored in the current directory.
        """
        if logger_path is not None:
            self.logger_path = logger_path

        file_handler = RotatingFileHandler(self.logger_path, maxBytes=1e6, backupCount=3)
        file_handler.setLevel(logging.INFO)

        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)

    def setLevel(self, loglevel: str) -> None:
        """Sets loglevel for both the logfile as well as stderr output

        Parameters
        ----------
        loglevel : str, Int
            Logging level, must be str or int.
        """
        self.logger.setLevel(loglevel)
        if self.logger.handlers:
            for handler in self.logger.handlers:
                handler.setLevel(loglevel)
        else:
            logging.basicConfig(level=loglevel)
