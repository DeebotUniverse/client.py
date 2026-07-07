from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.models import Credentials

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from deebot_client.authentication import RestConfiguration


async def test_authenticator_authenticate(rest_config: RestConfiguration) -> None:
    on_changed_called = asyncio.Event()

    async def on_changed(_: Credentials) -> None:
        if on_changed_called.is_set():
            pytest.fail("Event was already set")
        on_changed_called.set()

    with patch("deebot_client.authentication._AuthClient", spec_set=True) as api_client:
        login_mock: AsyncMock = api_client.return_value.login
        login_mock.return_value = Credentials(
            "token", "user_id", int(time.time() + 123456789)
        )
        authenticator = Authenticator(rest_config, "test", "test")

        unsub = authenticator.subscribe(on_changed)

        assert (await authenticator.authenticate()) == login_mock.return_value
        login_mock.assert_awaited_once()
        async with asyncio.timeout(0.1):
            await on_changed_called.wait()
            on_changed_called.clear()

        login_mock.reset_mock()

        # re-authenticate but this time we can use the cached credentials
        assert (await authenticator.authenticate()) == login_mock.return_value
        login_mock.assert_not_called()
        assert not on_changed_called.is_set()

        # Unsubscribe from authenticator
        unsub()

        # re-authenticate with force=True should call again the api
        assert (await authenticator.authenticate(force=True)) == login_mock.return_value
        login_mock.assert_awaited_once()
        assert not on_changed_called.is_set()


@pytest.mark.parametrize(
    (
        "country",
        "override_rest_url",
        "auth_domain",
        "expected_portal_url",
        "expected_login_url",
        "expected_auth_code_url",
        "expected_client_key",
        "expected_app_code",
    ),
    [
        (
            "CN",
            "http://example.com",
            "ecovacs.com",
            "http://example.com",
            "http://example.com",
            "http://example.com",
            "1520391301804",
            "global_e",
        ),
        (
            "CN",
            None,
            "ecovacs.com",
            "https://portal.ecouser.net",
            "https://gl-cn-api.ecovacs.cn",
            "https://gl-cn-openapi.ecovacs.cn",
            "1520391301804",
            "global_e",
        ),
        (
            "IT",
            "http://example.com",
            "ecovacs.com",
            "http://example.com",
            "http://example.com",
            "http://example.com",
            "1520391301804",
            "global_e",
        ),
        (
            "IT",
            None,
            "ecovacs.com",
            "https://portal-eu.ecouser.net",
            "https://gl-it-api.ecovacs.com",
            "https://gl-it-openapi.ecovacs.com",
            "1520391301804",
            "global_e",
        ),
        (
            "US",
            None,
            "yeedi.com",
            "https://portal-na.ecouser.net",
            "https://gl-us-api.yeedi.com",
            "https://gl-us-openapi.yeedi.com",
            "1581917520081",
            "yd_global_e",
        ),
    ],
)
def test_config_override_rest_url(
    session: ClientSession,
    country: str,
    override_rest_url: str | None,
    auth_domain: str,
    expected_portal_url: str,
    expected_login_url: str,
    expected_auth_code_url: str,
    expected_client_key: str,
    expected_app_code: str,
) -> None:
    """Test rest configuration."""
    config = create_rest_config(
        session=session,
        device_id="123",
        alpha_2_country=country,
        override_rest_url=override_rest_url,
        auth_domain=auth_domain,
    )
    assert config.portal_url == expected_portal_url
    assert config.login_url == expected_login_url
    assert config.auth_code_url == expected_auth_code_url
    assert config.client_key == expected_client_key
    assert config.app_code == expected_app_code
