"""Logging setup and utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional
import re


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""

    PATTERNS = {
        "api_key": re.compile(r"(api[_-]?key|key)\s*[:=]\s*([^\s]+)", re.IGNORECASE),
        "password": re.compile(r"(password|passwd)\s*[:=]\s*([^\s]+)", re.IGNORECASE),
        "token": re.compile(r"(token|auth)\s*[:=]\s*([^\s]+)", re.IGNORECASE),
        "uri": re.compile(r"(://[^:]+):([^@]+)@"),
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter record and mask sensitive data."""
        record.msg = self._mask_message(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._mask_message(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._mask_message(str(arg)) for arg in record.args)
        return True

    @staticmethod
    def _mask_message(message: str) -> str:
        """Mask sensitive patterns in message."""
        for pattern in SensitiveDataFilter.PATTERNS.values():
            message = pattern.sub(lambda m: m.group(0)[: 20] + "***", message)
        return message


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("aws_ai_data_migrator")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
