from img2catalog import Logger


def test_logger_path():
    """ Test if the logger path is set correctly when initialized without setting logger_path """
    logger = Logger('test_logger', logger_path=None)
    assert logger.logger_path == './test_logger.log'


def test_logger_path_add_filehandler():
    """ Test if the logger path is changed correctly when adding a file handler """
    logger = Logger('test_logger', logger_path=None)
    logger._add_file_handler("./new_logger_path.log")
    assert logger.logger_path == './new_logger_path.log'
