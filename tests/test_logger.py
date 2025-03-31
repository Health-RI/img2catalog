from img2catalog import Logger


def test_logger_path():
    logger = Logger('test_logger', logger_path=None)
    assert logger.logger_path == './test_logger.log'


def test_logger_path_add_filehandler():
    logger = Logger('test_logger', logger_path=None)
    logger._add_file_handler("./new_logger_path.log")
    assert logger.logger_path == './new_logger_path.log'
