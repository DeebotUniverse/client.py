from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

import pytest

from deebot_client.authentication import (
    Authenticator,
    RestConfiguration,
    _AuthClient,
    create_rest_config,
)
from deebot_client.models import Credentials

if TYPE_CHECKING:
    from collections.abc import Mapping

    from aiohttp import ClientSession


@pytest.mark.parametrize(
    ("country", "expected_host", "expected_path"),
    [
        pytest.param(
            "IT",
            "gl-it-api.ecovacs.com",
            "/v1/private/it/EN/test-device/global_e/3.14.0/google_play/1/user/login",
            id="global",
        ),
        pytest.param(
            "CN",
            "gl-cn-api.ecovacs.cn",
            "/v1/private/cn/EN/test-device/global_e/3.14.0/google_play/1/user/loginCheckMobile",
            id="china",
        ),
    ],
)
async def test_ecovacs_home_3_14_0_app_metadata_is_used_for_login(
    session: ClientSession,
    country: str,
    expected_host: str,
    expected_path: str,
) -> None:
    config = create_rest_config(
        session,
        device_id="test-device",
        alpha_2_country=country,
    )
    captured_sign_metadata: list[Mapping[str, str | int]] = []

    def capture_sign_metadata(
        params: dict[str, str | int],
        additional_sign_params: Mapping[str, str | int],
        *_signing_material: str,
    ) -> dict[str, str | int]:
        captured_sign_metadata.append(additional_sign_params)
        return params

    with (
        patch.object(
            session,
            "get",
            side_effect=RuntimeError("login request captured"),
        ) as get_mock,
        patch.object(
            _AuthClient,
            "_AuthClient__sign",
            new=staticmethod(capture_sign_metadata),
        ),
        patch("deebot_client.authentication.time.time", return_value=1_700_000_000),
    ):
        authenticator = Authenticator(config, "test-account", "test-password-hash")
        with pytest.raises(RuntimeError, match="login request captured"):
            await authenticator.authenticate()

    login_url = urlsplit(get_mock.call_args_list[0].args[0])
    assert login_url.netloc == expected_host
    assert login_url.path == expected_path
    assert {
        "lang": "EN",
        "appCode": "global_e",
        "appVersion": "3.14.0",
        "channel": "google_play",
        "deviceType": "1",
        "country": country.lower(),
        "deviceId": "test-device",
    }.items() <= captured_sign_metadata[0].items()


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
