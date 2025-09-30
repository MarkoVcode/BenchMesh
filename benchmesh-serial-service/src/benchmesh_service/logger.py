import logging


def setup_logger():
    logger = logging.getLogger("benchmesh_service")
    # Avoid adding duplicate handlers if called multiple times
    if getattr(logger, "_is_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler("benchmesh_service.log")
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