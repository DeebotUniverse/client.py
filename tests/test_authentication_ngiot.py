from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock

import pytest

from deebot_client.authentication import Authenticator, NgiotConfiguration
from deebot_client.exceptions import ApiError
from deebot_client.ngiot_client import NgiotClient
from deebot_client.sst_authentication import SstAuthenticator

if TYPE_CHECKING:
    from deebot_client.authentication import RestConfiguration


def test_configure_ngiot_normalizes_base_url_and_region(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    authenticator.configure_ngiot(
        NgiotConfiguration(
            base_url="api-base.dc-na.ww.ecouser.net/",
            region="dc-eu",
            user_agent="test-agent",
            timezone_name="Australia/Brisbane",
            timezone_offset_minutes=600,
            requested_ttl=300,
            refresh_skew=30,
        )
    )

    assert authenticator._ngiot_config.base_url == (
        "https://api-base.dc-na.ww.ecouser.net"
    )
    assert authenticator._ngiot_config.region == "eu"
    assert authenticator._ngiot_config.user_agent == "test-agent"
    assert authenticator._ngiot_config.timezone_name == "Australia/Brisbane"
    assert authenticator._ngiot_config.timezone_offset_minutes == 600
    assert authenticator._ngiot_config.requested_ttl == 300
    assert authenticator._ngiot_config.refresh_skew == 30


def test_attach_ngiot_requires_configured_base_url_or_region(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    with pytest.raises(ApiError, match="requires a configured NGIOT base_url or region"):
        authenticator.attach_ngiot()


def test_attach_ngiot_creates_transport_stack(rest_config: RestConfiguration) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    authenticator.attach_ngiot(
        NgiotConfiguration(
            region="dc-na",
            user_agent="test-agent",
            channel="Android",
            protocol_version="0.0.22",
            timezone_name="Australia/Brisbane",
            timezone_offset_minutes=600,
            requested_ttl=300,
            refresh_skew=30,
        )
    )

    assert authenticator._ngiot_base_url == "https://api-base.dc-na.ww.ecouser.net"
    assert isinstance(authenticator.sst_authenticator, SstAuthenticator)
    assert isinstance(authenticator.ngiot_client, NgiotClient)
    assert authenticator.sst_authenticator._base_url == (
        "https://api-base.dc-na.ww.ecouser.net"
    )
    assert authenticator.sst_authenticator._requested_ttl == 300
    assert authenticator.sst_authenticator._refresh_skew == 30
    assert authenticator.ngiot_client._config.user_agent == "test-agent"
    assert authenticator.ngiot_client._config.channel == "Android"
    assert authenticator.ngiot_client._config.protocol_version == "0.0.22"
    assert authenticator.ngiot_client._config.timezone_name == "Australia/Brisbane"
    assert authenticator.ngiot_client._config.timezone_offset_minutes == 600


def test_attach_ngiot_is_idempotent_for_same_base_url(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    authenticator.attach_ngiot(NgiotConfiguration(region="na"))
    first_sst_authenticator = authenticator.sst_authenticator
    first_ngiot_client = authenticator.ngiot_client
    authenticator.attach_ngiot(NgiotConfiguration(region="dc-na"))

    assert authenticator.sst_authenticator is first_sst_authenticator
    assert authenticator.ngiot_client is first_ngiot_client


def test_attach_ngiot_rejects_different_base_url_when_already_attached(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    authenticator.attach_ngiot(NgiotConfiguration(region="na"))

    with pytest.raises(ApiError, match="already attached with a different base URL"):
        authenticator.attach_ngiot(NgiotConfiguration(region="eu"))


async def test_teardown_clears_ngiot_transport(rest_config: RestConfiguration) -> None:
    authenticator = Authenticator(rest_config, "account", "password")
    sst_authenticator = AsyncMock(spec_set=SstAuthenticator)
    authenticator.sst_authenticator = cast("SstAuthenticator", sst_authenticator)
    authenticator.ngiot_client = cast("NgiotClient", object())
    authenticator._ngiot_base_url = "https://api-base.dc-na.ww.ecouser.net"

    await authenticator.teardown()

    sst_authenticator.teardown.assert_awaited_once()
    assert authenticator.sst_authenticator is None
    assert authenticator.ngiot_client is None
    assert authenticator._ngiot_base_url is None


@pytest.mark.parametrize(
    ("mqs_host", "expected"),
    [
        (
            "api-ngiot.dc-na.ww.ecouser.net",
            "https://api-base.dc-na.ww.ecouser.net",
        ),
        (
            "https://api-ngiot.dc-eu.ww.ecouser.net",
            "https://api-base.dc-eu.ww.ecouser.net",
        ),
        (
            "api-base.dc-ap.ww.ecouser.net",
            "https://api-base.dc-ap.ww.ecouser.net",
        ),
    ],
)
def test_derive_ngiot_base_url_from_mqs(mqs_host: str, expected: str) -> None:
    assert Authenticator._derive_ngiot_base_url_from_mqs(mqs_host) == expected


@pytest.mark.parametrize("mqs_host", ["", "localhost"])
def test_derive_ngiot_base_url_from_invalid_mqs_raises(mqs_host: str) -> None:
    with pytest.raises(ApiError):
        Authenticator._derive_ngiot_base_url_from_mqs(mqs_host)
