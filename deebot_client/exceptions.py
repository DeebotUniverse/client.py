"""Deebot client exception module."""


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


class NotInitializedError(DeebotError):
    """Thrown when not class was not initialized correctly."""
