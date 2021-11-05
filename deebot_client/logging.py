"""Logging filter module."""

import copy
from logging import Filter, Logger, LogRecord, getLogger
from typing import Set


class SanitizeFilter(Filter):
    """Filter to sensitive data."""

    # all lowercase
    _SANITIZE_LOG_KEYS: Set[str] = {
        "auth",
        "token",
        "id",
        "login",
        "mobile",
        "user",
        "email",
    }

    def filter(self, record: LogRecord) -> bool:
        """Filter log record."""
        # The call signature matches string interpolation: args can be a tuple or a lone dict
        if isinstance(record.args, dict):
            record.args = self._sanitize_dict(record.args)
        else:
            record.args = tuple(
                self._sanitize_dict(value) if isinstance(value, dict) else value
                for value in record.args
            )

        return True

    def _sanitize_dict(self, data: dict) -> dict:
        """Sanitize data (remove personal data)."""
        sanitized_data = None
        for key in data.keys():
            if any(substring in key.lower() for substring in self._SANITIZE_LOG_KEYS):
                if sanitized_data is None:
                    sanitized_data = copy.deepcopy(data)
                sanitized_data[key] = "[REMOVED]"

        return sanitized_data if sanitized_data else data


def get_logger(name: str) -> Logger:
    """Get logger with filter."""
    logger = getLogger(name)
    logger.addFilter(SanitizeFilter())
    return logger
