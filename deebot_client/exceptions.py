"""Deebot client exception module."""
from __future__ import annotations


class DeebotError(Exception):
    """Deebot error."""


class AuthenticationError(DeebotError):
    """Authentication error."""


class InvalidAuthenticationError(AuthenticationError):
    """Invalid authentication error."""


class ApiError(DeebotError):
    """Api error."""


class MapError(DeebotError):
    """Map error."""
