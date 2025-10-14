"""Logging filter module."""

from __future__ import annotations

from logging import Filter, Logger, LogRecord, getLogger
from typing import Any


class SanitizeFilter(Filter):
    """Filter to sensitive data."""

    # all lowercase
    _SANITIZE_LOG_KEYS = (
        "auth",
        "did",
        "email",
        "login",
        "mobile",
        "token",
        "uid",
        "user",
    )

    def filter(self, record: LogRecord) -> bool:
        """Filter log record."""
        # The call signature matches string interpolation: args can be a tuple or a dict
        if isinstance(record.args, dict):
            record.args = self._sanitize_data(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(self._sanitize_data(value) for value in record.args)

        return True

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data (remove personal data)."""
        if isinstance(data, set | list):
            return [self._sanitize_data(entry) for entry in data]

        if not isinstance(data, dict):
            return data

        sanitized_data = None
        for key, value in data.items():
            if any(substring in key.lower() for substring in self._SANITIZE_LOG_KEYS):
                # Lazy shallow copy on first modification
                if sanitized_data is None:
                    sanitized_data = dict(data)
                sanitized_data[key] = "[REMOVED]"
            elif isinstance(value, set | list | dict):
                # Recursively sanitize nested structures
                sanitized_value = self._sanitize_data(value)
                if (
                    sanitized_value is not value
                ):  # Only copy if nested data was modified
                    if sanitized_data is None:
                        sanitized_data = dict(data)
                    sanitized_data[key] = sanitized_value

        return sanitized_data if sanitized_data else data


def get_logger(name: str) -> Logger:
    """Get logger with filter."""
    logger = getLogger(name)
    logger.addFilter(SanitizeFilter())
    return logger
