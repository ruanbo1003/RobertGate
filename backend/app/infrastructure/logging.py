import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Access log
    access_handler = RotatingFileHandler(
        f"{log_dir}/access.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    access_handler.setFormatter(fmt)
    access_logger = logging.getLogger("app.access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_handler)

    # Error log
    error_handler = RotatingFileHandler(
        f"{log_dir}/error.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    error_handler.setFormatter(fmt)
    error_logger = logging.getLogger("app.error")
    error_logger.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)

    # Console
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("app").addHandler(console)
