import logging

def get_logger(name="nail_ecommerce_project"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        # Use simple console output
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger