"""Deebot client exception module."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientTimeout


class DeebotError(Exception):
    """Deebot error."""


class AuthenticationError(DeebotError):
    """Authentication error."""


class InvalidAuthenticationError(AuthenticationError):
    """Invalid authentication error."""


class DeviceVerificationRequiredError(AuthenticationError):
    """Device verification is required before authentication."""


class InvalidVerificationCodeError(InvalidAuthenticationError):
    """Invalid or expired device verification code."""


class ApiError(DeebotError):
    """Api error."""


class ApiTimeoutError(ApiError):
    """Api timeout error."""

    def __init__(self, path: str, timeout: ClientTimeout, *args: object) -> None:
        super().__init__(f"Timeout ({timeout}) reached on path: {path}", *args)


class MapError(DeebotError):
    """Map error."""


class MqttError(DeebotError):
    """Mqtt error."""
