import logging

from uvicorn.logging import DefaultFormatter


# Formatter

_handler = logging.StreamHandler()
_handler.setFormatter(
    DefaultFormatter(
        fmt="%(levelprefix)s [%(name)s] %(message)s",
        use_colors=None
    )
)


# Logger

def _configure_base_logger() -> logging.Logger:
    logger = logging.getLogger("mairepo")

    if _handler not in logger.handlers:
        logger.handlers.clear()
        logger.addHandler(_handler)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.disabled = False

    return logger


def get_logger(name:str) -> logging.Logger:
    """
    Return a logger using the mairepo console format.

    Args:
        name: Name used to identify the logger.

    Returns:
        logging.Logger: Logger configured with the mairepo formatter.
    """
    base_logger = _configure_base_logger()

    if not name or name == "mairepo":
        return base_logger

    logger_name = name if name.startswith("mairepo.") else f"mairepo.{name}"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    logger.disabled = False

    return logger
