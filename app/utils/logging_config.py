import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def configure_logging() -> logging.Logger:
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / "LOGS"
    log_dir.mkdir(exist_ok=True)

    log_level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    file_handler = RotatingFileHandler(
        log_dir / f"app_{now}.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    return logging.getLogger("VehicleUsageAPI")
