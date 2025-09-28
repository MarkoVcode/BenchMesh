import logging

def setup_logger():
    logger = logging.getLogger("benchmesh_service")
    logger.setLevel(logging.DEBUG)

    # Create file handler
    fh = logging.FileHandler("benchmesh_service.log")
    fh.setLevel(logging.DEBUG)

    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

logger = setup_logger()