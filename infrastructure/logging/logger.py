"""Colored logging configuration for the Artificer monorepo.

This module provides automatic colored logging setup with environment-based
configuration. The logging is configured globally when the module is imported,
providing consistent colored output across all services.
"""

import datetime
import logging
import os
import sys
from typing import ClassVar


class ColoredFormatter(logging.Formatter):
    """Logging formatter that adds ANSI color codes to log messages.

    This formatter applies different colors to log messages based on their
    severity level and uses millisecond precision timestamps for DEBUG logs.

    Attributes:
        COLORS: Dictionary mapping log level names to ANSI color codes.
    """

    # ANSI color codes
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[90m",  # Grey
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset to normal
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color codes and appropriate timestamp.

        Args:
            record: LogRecord instance containing log information.

        Returns:
            Formatted and colorized log message string.
        """
        # Use different timestamp formats based on log level
        if record.levelname == "DEBUG":
            # Debug gets milliseconds
            timestamp = datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
            message = f"{timestamp} - {record.levelname} - {record.name} - {record.getMessage()}"
        else:
            # All other levels use standard format without milliseconds
            message = super().format(record)

        # Add color based on log level
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        return f"{color}{message}{reset}"


def _setup_global_logging() -> None:
    """Configure global logging with colored output.

    Sets up the root logger with ColoredFormatter and configures log level
    from LOG_LEVEL environment variable. This function is idempotent and
    runs automatically when the module is imported.
    """
    root_logger = logging.getLogger()

    # Only setup once
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        # Set log level from environment variable or default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, log_level, logging.INFO)
        root_logger.setLevel(level)

        # Also set level on all existing loggers
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(level)


# This runs automatically when anyone imports this module
_setup_global_logging()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger with colored output.

    Creates or retrieves a logger with the specified name and sets its level
    from the LOG_LEVEL environment variable.

    Args:
        name: Name for the logger, typically the module or class name.

    Returns:
        Configured logger instance with colored formatting.
    """
    logger = logging.getLogger(name)

    # Set log level from environment variable each time
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(level)

    return logger
