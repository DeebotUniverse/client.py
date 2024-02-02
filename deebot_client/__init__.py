"""Deebot client module."""
from __future__ import annotations

import logging

from deebot_client.logging_filter import SanitizeFilter

# Set library sanitize filter
logging.getLogger(__name__).addFilter(SanitizeFilter())
