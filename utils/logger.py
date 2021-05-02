import logging
import datetime

LOG_FILE_PATH = "/home/gorana/PycharmProjects/SurveyGenerator/survey-generator/logs/app-{}.log".format(str(datetime.datetime.utcnow()))

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
