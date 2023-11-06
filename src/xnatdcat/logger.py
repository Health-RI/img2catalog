import sys
import logging
from logging import StreamHandler, FileHandler


class Logger:
    def __init__(self, logger_name: str):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        console_handler = StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)

        file_handler = FileHandler(f'./{logger_name}.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        self.logger = logger
        self.start_run()

    def start_run(self) -> None:
        self.logger.info('======== New run =========')
