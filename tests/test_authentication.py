from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.const import AUTH_DOMAIN_ECOVACS, AUTH_DOMAIN_YEEDI
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
        "auth_domain",
        "override_rest_url",
        "expected_portal_url",
        "expected_login_url",
        "expected_auth_code_url",
    ),
    [
        (
            "CN",
            AUTH_DOMAIN_ECOVACS,
            "http://example.com",
            "http://example.com",
            "http://example.com",
            "http://example.com",
        ),
        (
            "CN",
            AUTH_DOMAIN_ECOVACS,
            None,
            "https://portal.ecouser.net",
            "https://gl-cn-api.ecovacs.cn",
            "https://gl-cn-openapi.ecovacs.cn",
        ),
        (
            "IT",
            AUTH_DOMAIN_ECOVACS,
            "http://example.com",
            "http://example.com",
            "http://example.com",
            "http://example.com",
        ),
        (
            "IT",
            AUTH_DOMAIN_ECOVACS,
            None,
            "https://portal-eu.ecouser.net",
            "https://gl-it-api.ecovacs.com",
            "https://gl-it-openapi.ecovacs.com",
        ),
        (
            "CN",
            AUTH_DOMAIN_YEEDI,
            None,
            "https://portal.ecouser.net",
            "https://gl-cn-api.yeedi.cn",
            "https://gl-cn-openapi.yeedi.cn",
        ),
        (
            "IT",
            AUTH_DOMAIN_YEEDI,
            None,
            "https://portal-eu.ecouser.net",
            "https://gl-it-api.yeedi.com",
            "https://gl-it-openapi.yeedi.com",
        ),
    ],
)
def test_config_override_rest_url(
    session: ClientSession,
    country: str,
    auth_domain: str,
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
        auth_domain=auth_domain,
        override_rest_url=override_rest_url,
    )
    assert config.portal_url == expected_portal_url
    assert config.login_url == expected_login_url
    assert config.auth_code_url == expected_auth_code_url


def test_config_unsupported_auth_domain(session: ClientSession) -> None:
    with pytest.raises(ValueError, match=r"Unsupported auth domain: example\.com"):
        create_rest_config(
            session=session,
            device_id="123",
            alpha_2_country="IT",
            auth_domain="example.com",
        )


@pytest.mark.parametrize(
    ("auth_domain", "expected"),
    [
        (
            AUTH_DOMAIN_ECOVACS,
            {
                "app_code": "global_e",
                "app_version": "1.6.3",
                "get_auth_code_biz_type": "ECOVACS_IOT",
                "org_global": "ECOWW",
                "org_china": "ECOCN",
                "command_client_version": "1.67.3",
                "command_app_version": "1.3.1",
            },
        ),
        (
            AUTH_DOMAIN_YEEDI,
            {
                "app_code": "yd_global_e",
                "app_version": "1.3.0",
                "get_auth_code_biz_type": "",
                "org_global": "ECOYDWW",
                "org_china": "ECOYDCN",
                "command_client_version": "1.94.76",
                "command_app_version": "1.3.0",
            },
        ),
    ],
)
def test_config_auth_domain_metadata(
    session: ClientSession, auth_domain: str, expected: dict[str, str]
) -> None:
    config = create_rest_config(
        session=session,
        device_id="123",
        alpha_2_country="IT",
        auth_domain=auth_domain,
    )

    assert config.auth.app_code == expected["app_code"]
    assert config.auth.app_version == expected["app_version"]
    assert config.auth.get_auth_code_biz_type == expected["get_auth_code_biz_type"]
    assert config.auth.org_global == expected["org_global"]
    assert config.auth.org_china == expected["org_china"]
    assert config.auth.command_client_version == expected["command_client_version"]
    assert config.auth.command_app_version == expected["command_app_version"]


def test_authenticator_command_query_params(session: ClientSession) -> None:
    config = create_rest_config(
        session=session,
        device_id="123",
        alpha_2_country="IT",
        auth_domain=AUTH_DOMAIN_YEEDI,
    )
    authenticator = Authenticator(config, "test", "test")

    assert authenticator.get_command_query_params(
        Credentials("token", "user_id", 9999),
        mid="class",
        did="did",
        td="q",
    ) == {
        "mid": "class",
        "did": "did",
        "td": "q",
        "u": "user_id",
        "cv": "1.94.76",
        "t": "a",
        "av": "1.3.0",
    }
