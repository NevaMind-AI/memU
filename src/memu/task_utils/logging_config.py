"""
Structured logging configuration for Celery workers.

This module provides JSON-formatted logging for production environments
and human-readable logging for development.
"""

import json
import logging
import logging.config
import sys
from typing import Any, ClassVar


class JSONFormatter(logging.Formatter):
    """
    Format logs as JSON for structured logging.

    Includes standard fields (timestamp, level, message) and
    custom fields from the 'extra' parameter (task_id, user_id, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields from record
        extra_fields = [
            "task_id",
            "user_id",
            "resource_url",
            "modality",
            "error_type",
            "retry_count",
            "countdown",
        ]

        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add stack trace if present
        if record.stack_info:
            log_data["stack_trace"] = record.stack_info

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.

    Adds ANSI color codes for better readability in terminal.
    """

    COLORS: ClassVar[dict] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def configure_celery_logging(
    log_level: str = "INFO",
    use_json: bool = True,
    log_file: str | None = None,
) -> None:
    """
    Configure logging for Celery workers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: If True, use JSON formatter; if False, use standard formatter
        log_file: Optional log file path for file logging
    """
    handlers: dict[str, Any] = {}

    # Console handler
    console_handler = {
        "class": "logging.StreamHandler",
        "stream": sys.stdout,
        "formatter": "json" if use_json else "colored",
    }
    handlers["console"] = console_handler

    # file handler (optional)
    if log_file:
        file_handler = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "json" if use_json else "standard",
        }
        handlers["file"] = file_handler

    formatters = {
        "json": {
            "()": JSONFormatter,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "colored": {
            "()": ColoredFormatter,
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            "memu": {
                "level": log_level,
                "handlers": list(handlers.keys()),
                "propagate": False,
            },
            "celery": {
                "level": "INFO",
                "handlers": list(handlers.keys()),
                "propagate": False,
            },
            "celery.worker": {
                "level": "INFO",
                "handlers": list(handlers.keys()),
                "propagate": False,
            },
            "celery.task": {
                "level": "INFO",
                "handlers": list(handlers.keys()),
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)
