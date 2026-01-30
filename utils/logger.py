import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_filename = f"rpa_SOC{datetime.now().strftime('%Y-%m-%d')}.log"
LOG_FILE = LOG_DIR / log_filename


def setup_logger():
    logger = logging.getLogger("RPA")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
