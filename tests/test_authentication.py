from __future__ import annotations

import asyncio
import hashlib
import time
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.authentication import (
    Authenticator,
    RestConfiguration,
    _AuthClient,
    create_rest_config,
)
from deebot_client.models import Credentials

if TYPE_CHECKING:
    from aiohttp import ClientSession


async def test_login_uses_current_app_version_in_url_and_signature() -> None:
    config = RestConfiguration(
        session=cast("ClientSession", AsyncMock()),
        device_id="test-device",
        country="IT",
        portal_url="https://portal.example",
        login_url="https://login.example",
        auth_code_url="https://auth.example",
    )
    auth_client = _AuthClient(config, "test-account", "test-password-hash")
    timestamp = 1_700_000_000.125

    with (
        patch("deebot_client.authentication.time.time", return_value=timestamp),
        patch.object(
            auth_client, "_AuthClient__do_auth_response", new_callable=AsyncMock
        ) as response_mock,
    ):
        await auth_client._AuthClient__call_login_api(  # type: ignore[attr-defined]
            "test-account", "test-password-hash"
        )

    call_args = response_mock.await_args
    assert call_args is not None
    url, params = call_args.args
    expected_sign_data = {
        "account": "test-account",
        "appCode": "global_e",
        "appVersion": "3.14.0",
        "authTimespan": int(timestamp * 1000),
        "authTimeZone": "GMT-8",
        "channel": "google_play",
        "country": "it",
        "deviceId": "test-device",
        "deviceType": "1",
        "lang": "EN",
        "password": "test-password-hash",
        "requestId": hashlib.md5(
            str(timestamp).encode(), usedforsecurity=False
        ).hexdigest(),
    }
    sign_on_text = (
        "1520391301804"
        + "".join(
            f"{key}={expected_sign_data[key]}" for key in sorted(expected_sign_data)
        )
        + "6c319b2a5cd3e66e39159c2e28f2fce9"
    )
    expected_auth_sign = hashlib.md5(
        sign_on_text.encode(), usedforsecurity=False
    ).hexdigest()

    assert url == (
        "https://login.example/v1/private/it/EN/test-device/"
        "global_e/3.14.0/google_play/1/user/login"
    )
    assert params["authSign"] == expected_auth_sign


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
        "expected_portal_url",
        "expected_login_url",
        "expected_auth_code_url",
    ),
    [
        (
            "CN",
            "http://example.com",
            "http://example.com",
            "http://example.com",
            "http://example.com",
        ),
        (
            "CN",
            None,
            "https://portal.ecouser.net",
            "https://gl-cn-api.ecovacs.cn",
            "https://gl-cn-openapi.ecovacs.cn",
        ),
        (
            "IT",
            "http://example.com",
            "http://example.com",
            "http://example.com",
            "http://example.com",
        ),
        (
            "IT",
            None,
            "https://portal-eu.ecouser.net",
            "https://gl-it-api.ecovacs.com",
            "https://gl-it-openapi.ecovacs.com",
        ),
    ],
)
def test_config_override_rest_url(
    session: ClientSession,
    country: str,
    override_rest_url: str | None,
    expected_portal_url: str,
    expected_login_url: str,
    expected_auth_code_url: str,
) -> None:
    """Test rest configuration."""
    config = create_rest_config(
        session=session,
        device_id="123",
        alpha_2_country=country,
        override_rest_url=override_rest_url,
    )
    assert config.portal_url == expected_portal_url
    assert config.login_url == expected_login_url
    assert config.auth_code_url == expected_auth_code_url
