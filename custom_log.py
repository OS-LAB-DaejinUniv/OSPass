# Logging Custom 
import logging
import time
from datetime import datetime, timezone, timedelta

class LoggerSetup:
    '''
    logging level에 따라 색상을 다르게 함
    logging에 timestamp 추가
    '''
    def __init__(self):
        self.logger = self._initialize_logger()

    class CustomFormatter(logging.Formatter):
        
        COLOR_MAP = {
            logging.DEBUG: "\033[94m",    # Blue
            logging.INFO: "\033[92m",     # Green
            logging.WARNING: "\033[93m",  # Yellow
            logging.ERROR: "\033[91m",    # Red
            logging.CRITICAL: "\033[1;31m",  # Bold Red
        }
        RESET = "\033[0m"

        def format(self, record):
            log_color = self.COLOR_MAP.get(record.levelno, self.RESET)
            log_message = super().format(record)
            return f"{log_color}{log_message}{self.RESET}"

    def _initialize_logger(self):
        # Set up logger with the custom formatter
        log_format = "%(asctime)s [%(levelname)s]: %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        # UTC -> KST
        def custom_time(*args):
            kst = timezone(timedelta(hours=9)) 
            return datetime.now(tz=kst).timetuple()
        
        logging.Formatter.converter = custom_time
        
        logger = logging.getLogger("custom_logger")

        # Check if the logger already has handlers before adding new ones
        if not logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setFormatter(self.CustomFormatter(fmt=log_format, datefmt=date_format))
            logger.setLevel(logging.DEBUG)  # Set default log level
            logger.addHandler(handler)

        return logger
    