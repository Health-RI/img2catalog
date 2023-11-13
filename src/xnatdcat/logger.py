import sys
import logging
from logging import StreamHandler, FileHandler


class Logger:
    """Logging class that logs Warnings to STDOUT and Info to file.

    Parameters
    ----------
    logger_name : str
        Internal name of logger. This log file will be called './{logger_name}.log'.

    """
    def __init__(self, logger_name: str):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # output to stderr as to allow clean piping of output
        console_handler = StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)

        file_handler = FileHandler(f'./{logger_name}.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        self.logger = logger
        self.start_run()

    def start_run(self) -> None:
        """Prints a line in the logs signifying a new run."""
        self.logger.info('======== New run =========')

    def setLevel(self, loglevel):
        if self.logger.handlers:
            for handler in self.logger.handlers:
                handler.setLevel(loglevel)
        else:
            logging.basicConfig(level=loglevel)
