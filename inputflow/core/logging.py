import sys

from loguru import logger


def get_logger(name: str = "inputflow", log_file: str = "inputflow.log"):
    """
    Configures and returns a Loguru logger instance.

    Logs will be output to stdout and a specified log file.
    """
    logger.remove()  # Remove default handler

    # Add handler for stdout
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        diagnose=False,
    )

    # Add handler for log file
    logger.add(
        log_file,
        level="INFO",  # Log all messages to file
        rotation="10 MB",  # Rotate file after 10 MB
        compression="zip",  # Compress rotated files
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        diagnose=False,
    )

    return logger.bind(name=name)
