"""
Logging configuration module for MemU.

Provides centralized logging configuration with consistent formatting and levels.
"""

import logging
import sys
from typing import Optional


class FlushingStreamHandler(logging.StreamHandler):
    """Stream handler that flushes after each log record."""

    def emit(self, record):
        """Emit a record, ensuring the stream is flushed."""
        try:
            super().emit(record)
            self.flush()
            # Ensure immediate flush to terminal
            if hasattr(self.stream, "flush"):
                self.stream.flush()
        except Exception:
            self.handleError(record)


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for better readability."""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if hasattr(record, "levelname"):
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    name: str = "memu",
    level: str = "INFO",
    format_string: Optional[str] = None,
    use_colors: bool = True,
    enable_flush: bool = True,
) -> logging.Logger:
    """
    Setup logging configuration for MemU.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string
        use_colors: Whether to use colored output
        enable_flush: Whether to enable auto-flush for real-time output

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Prevent log propagation to avoid duplicate messages when running under uvicorn
    logger.propagate = False

    # Create console handler with optional auto-flush
    if enable_flush:
        console_handler = FlushingStreamHandler(sys.stdout)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Create formatter
    if format_string is None:
        format_string = (
            "%(asctime)s | %(name)s:%(lineno)d | %(levelname)s | %(message)s"
        )

    if use_colors and sys.stdout.isatty():
        formatter = ColoredFormatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    else:
        formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "memu") -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    logger = logging.getLogger(name)
    
    # Ensure the logger doesn't propagate to prevent duplicate messages
    # when running under uvicorn or other logging frameworks
    # logger.propagate = False
    
    return logger


# Default logger instance
default_logger = setup_logging()
