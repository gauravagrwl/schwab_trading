import logging
import os
from logging.handlers import RotatingFileHandler



LOGGING_FORMAT = "%(asctime)s %(levelname)-8s %(name)s:%(module)s.%(funcName)s:%(lineno)d │ %(message)s"
LOG_DIR = "./logs"
LOG_FILE_PATH = os.path.join(LOG_DIR, "schwab_trading.log")
MAX_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 10000
CLIENT_ID=""
CLIENT_SECRET=""
REDIRECT_URI=""
TOKEN_PATH="./tokens/schwab_tokens.json"



class LoggerConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance.logger

    def _setup(self):
        os.makedirs(LOG_DIR, exist_ok=True)

        # --- Root logger ---
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.DEBUG)

        # Console handler (INFO+)
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            ch = logging.StreamHandler()
            # ch = TqdmLoggingHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter(LOGGING_FORMAT))
            root_logger.addHandler(ch)

        # File handler (ERROR+)
        if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
            fh = RotatingFileHandler(
                LOG_FILE_PATH,
                maxBytes=MAX_SIZE,
                backupCount=BACKUP_COUNT,
                encoding="utf-8",
            )
            fh.setLevel(logging.INFO)
            fh.setFormatter(logging.Formatter(LOGGING_FORMAT))
            root_logger.addHandler(fh)

        # --- Custom app logger ---
        self.logger = logging.getLogger("schwab_trading")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = True


# Usage
logger = LoggerConfig()
logger.info("Logger initialized.")
logger.error("This is an error message.")




