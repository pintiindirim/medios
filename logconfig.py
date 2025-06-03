# logconfig.py
import logging
import os
logger = logging.getLogger("central_services")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)
logger.setLevel(numeric_level)
fh = logging.FileHandler("media_log.txt", encoding="utf-8")
fh.setLevel(numeric_level)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(numeric_level)
ch.setFormatter(formatter)
logger.addHandler(ch)
def flush_logs():
    for handler in logger.handlers:
        handler.flush()
