from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.exceptions import ApiError, DeviceVerificationRequiredError

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.api_client import ApiClient


async def test_get_devices_reraises_deebot_error(
    api_client: ApiClient, authenticator: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that a deebot error is re-raised with its original type."""
    # both tasks fail with the same error
    authenticator.post_authenticated.side_effect = DeviceVerificationRequiredError(
        "verification required"
    )

    with pytest.raises(
        DeviceVerificationRequiredError, match="verification required"
    ) as ex:
        await api_client.get_devices()

    assert isinstance(ex.value.__context__, BaseExceptionGroup)
    assert "Multiple different exceptions occurred" not in caplog.text


async def test_get_devices_logs_different_errors(
    api_client: ApiClient, authenticator: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that the not raised errors are logged."""
    authenticator.post_authenticated.side_effect = [
        DeviceVerificationRequiredError("verification required"),
        ApiError("something else"),
    ]

    with pytest.raises(DeviceVerificationRequiredError, match="verification required"):
        await api_client.get_devices()

    assert (
        "Multiple different exceptions occurred, raising only "
        "DeviceVerificationRequiredError: verification required"
    ) in caplog.text
    # all exceptions are logged with their stacktrace
    assert "ExceptionGroup: unhandled errors in a TaskGroup" in caplog.text
    assert "DeviceVerificationRequiredError: verification required" in caplog.text
    assert "ApiError: something else" in caplog.text
    assert "api_client.py" in caplog.text


async def test_get_devices_wraps_unexpected_error(
    api_client: ApiClient, authenticator: Mock
) -> None:
    """Test that an unexpected error is wrapped into an ApiError."""
    authenticator.post_authenticated.side_effect = RuntimeError("boom")

    with pytest.raises(ApiError, match="Error on getting devices"):
        await api_client.get_devices()
