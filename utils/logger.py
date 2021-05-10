import logging
import datetime

from pathlib import Path

LOG_FILE_PATH = "./logs/app-{}.log".format(str(datetime.datetime.utcnow()))
if not Path(LOG_FILE_PATH).parent.exists():
    Path(LOG_FILE_PATH).parent.mkdir(parents=True)

# Create a custom logger
logger = logging.getLogger(__name__)

# Create handlers
console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE_PATH)
# file_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)
