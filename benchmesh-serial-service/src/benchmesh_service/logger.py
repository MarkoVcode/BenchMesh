import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger():
    logger = logging.getLogger("benchmesh_service")
    # Avoid adding duplicate handlers if called multiple times
    if getattr(logger, "_is_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)

    # Use user data directory if BENCHMESH_DATA_DIR is set (Electron/production mode)
    # Otherwise fall back to repository root logs directory (development mode)
    data_dir = os.getenv("BENCHMESH_DATA_DIR")
    if data_dir:
        log_dir = Path(data_dir) / "logs"
    else:
        # Development mode: use repository root logs directory
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"

    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "benchmesh_service.log"

    # Use rotating file handler to prevent logs from growing infinitely
    # Max 10MB per file, keep 5 backup files (total ~50MB max)
    fh = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    # Prevent propagation to root logger (avoids duplicate logs via root handlers)
    logger.propagate = False
    # Mark as configured
    logger._is_configured = True

    return logger


logger = setup_logger()