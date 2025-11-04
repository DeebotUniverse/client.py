from __future__ import annotations

import asyncio
from http import HTTPStatus
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from aiohttp import ClientResponseError
import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.exceptions import (
    ApiError,
    ApiTimeoutError,
    AuthenticationError,
    InvalidAuthenticationError,
)
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


async def test_authenticator_expired_credentials(rest_config: RestConfiguration) -> None:
    """Test re-authentication when credentials are expired."""
    with patch("deebot_client.authentication._AuthClient", spec_set=True) as api_client:
        login_mock: AsyncMock = api_client.return_value.login
        # First set of credentials that are already expired
        login_mock.return_value = Credentials(
            "token1", "user_id", int(time.time() - 1)
        )
        authenticator = Authenticator(rest_config, "test", "test")

        # Should call login again because credentials are expired
        await authenticator.authenticate()
        assert login_mock.await_count == 1

        # Update to non-expired credentials
        login_mock.return_value = Credentials(
            "token2", "user_id", int(time.time() + 123456789)
        )

        # Should call login again since previous credentials were expired
        await authenticator.authenticate()
        assert login_mock.await_count == 2


async def test_authenticator_post_authenticated(rest_config: RestConfiguration) -> None:
    """Test post_authenticated method."""
    with patch("deebot_client.authentication._AuthClient", spec_set=True) as api_client:
        login_mock: AsyncMock = api_client.return_value.login
        post_mock: AsyncMock = api_client.return_value.post

        login_mock.return_value = Credentials(
            "token", "user_id", int(time.time() + 123456789)
        )
        post_mock.return_value = {"result": "success"}

        authenticator = Authenticator(rest_config, "test", "test")

        result = await authenticator.post_authenticated(
            "test/path",
            {"data": "value"},
            query_params={"param": "value"},
            headers={"header": "value"}
        )

        assert result == {"result": "success"}
        post_mock.assert_awaited_once()


async def test_authenticator_teardown(rest_config: RestConfiguration) -> None:
    """Test authenticator teardown."""
    with patch("deebot_client.authentication._AuthClient", spec_set=True) as api_client:
        login_mock: AsyncMock = api_client.return_value.login
        login_mock.return_value = Credentials(
            "token", "user_id", int(time.time() + 123456789)
        )

        authenticator = Authenticator(rest_config, "test", "test")
        await authenticator.authenticate()

        # Teardown should not raise any exceptions
        await authenticator.teardown()


async def test_auth_client_login_success(rest_config: RestConfiguration) -> None:
    """Test _AuthClient login flow."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "test@example.com", "password_hash")

    mock_response_login = {
        "code": "0000",
        "data": {
            "uid": "user123",
            "accessToken": "access_token_123"
        }
    }

    mock_response_auth = {
        "code": "0000",
        "data": {
            "authCode": "auth_code_123"
        }
    }

    mock_response_token = {
        "result": "ok",
        "userId": "user123",
        "token": "final_token",
        "last": "604800000"
    }

    with patch.object(rest_config.session, 'get') as mock_get, \
         patch.object(rest_config.session, 'post') as mock_post:

        # Setup mock for login API call
        login_response = AsyncMock()
        login_response.status = HTTPStatus.OK
        login_response.headers = {"content-type": "application/json"}
        login_response.json = AsyncMock(return_value=mock_response_login)
        login_response.raise_for_status = Mock()

        # Setup mock for auth API call
        auth_response = AsyncMock()
        auth_response.status = HTTPStatus.OK
        auth_response.headers = {"content-type": "application/json"}
        auth_response.json = AsyncMock(return_value=mock_response_auth)
        auth_response.raise_for_status = Mock()

        # Setup mock for token login API call
        token_response = AsyncMock()
        token_response.status = HTTPStatus.OK
        token_response.json = AsyncMock(return_value=mock_response_token)
        token_response.raise_for_status = Mock()

        mock_get.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=login_response)),
            AsyncMock(__aenter__=AsyncMock(return_value=auth_response))
        ]

        mock_post.return_value.__aenter__ = AsyncMock(return_value=token_response)

        credentials = await auth_client.login()

        assert credentials.user_id == "user123"
        assert credentials.token == "final_token"
        assert credentials.expires_at > time.time()


async def test_auth_client_invalid_credentials(rest_config: RestConfiguration) -> None:
    """Test _AuthClient with invalid credentials."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "bad@example.com", "bad_password")

    mock_response = {
        "code": "1005",
        "msg": "Invalid credentials"
    }

    with patch.object(rest_config.session, 'get') as mock_get:
        response = AsyncMock()
        response.headers = {"content-type": "application/json"}
        response.json = AsyncMock(return_value=mock_response)
        response.raise_for_status = Mock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=response)

        with pytest.raises(InvalidAuthenticationError):
            await auth_client.login()


async def test_auth_client_authentication_error(rest_config: RestConfiguration) -> None:
    """Test _AuthClient with authentication error."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "test@example.com", "password")

    mock_response = {
        "code": "5000",
        "msg": "Server error"
    }

    with patch.object(rest_config.session, 'get') as mock_get:
        response = AsyncMock()
        response.headers = {"content-type": "application/json"}
        response.json = AsyncMock(return_value=mock_response)
        response.raise_for_status = Mock()
        mock_get.return_value.__aenter__ = AsyncMock(return_value=response)

        with pytest.raises(AuthenticationError, match="failure code 5000"):
            await auth_client.login()


async def test_auth_client_post_timeout(rest_config: RestConfiguration) -> None:
    """Test _AuthClient post with timeout."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "test@example.com", "password")

    with patch.object(rest_config.session, 'post') as mock_post:
        mock_post.side_effect = TimeoutError("Request timed out")

        with pytest.raises(ApiTimeoutError):
            await auth_client.post("test/path", {})


async def test_auth_client_post_bad_gateway_retry(rest_config: RestConfiguration) -> None:
    """Test _AuthClient post with 502 Bad Gateway retry."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "test@example.com", "password")

    # First call returns 502, subsequent calls should succeed
    response_error = AsyncMock()
    response_error.status = HTTPStatus.BAD_GATEWAY
    response_error.raise_for_status = Mock(
        side_effect=ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=HTTPStatus.BAD_GATEWAY,
            message="Bad Gateway"
        )
    )

    response_success = AsyncMock()
    response_success.status = HTTPStatus.OK
    response_success.json = AsyncMock(return_value={"result": "ok"})
    response_success.raise_for_status = Mock()

    with patch.object(rest_config.session, 'post') as mock_post, \
         patch('asyncio.sleep', new_callable=AsyncMock):
        mock_post.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=response_error)),
            AsyncMock(__aenter__=AsyncMock(return_value=response_success))
        ]

        result = await auth_client.post("test/path", {})
        assert result == {"result": "ok"}
        assert mock_post.call_count == 2


async def test_auth_client_post_client_error(rest_config: RestConfiguration) -> None:
    """Test _AuthClient post with client error."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "test@example.com", "password")

    response_error = AsyncMock()
    response_error.status = HTTPStatus.INTERNAL_SERVER_ERROR
    response_error.raise_for_status = Mock(
        side_effect=ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            message="Internal Server Error"
        )
    )

    with patch.object(rest_config.session, 'post') as mock_post:
        mock_post.return_value.__aenter__ = AsyncMock(return_value=response_error)

        with pytest.raises(ApiError):
            await auth_client.post("test/path", {})


async def test_auth_client_login_token_retry(rest_config: RestConfiguration) -> None:
    """Test _AuthClient login with token error and retry."""
    from deebot_client.authentication import _AuthClient

    auth_client = _AuthClient(rest_config, "test@example.com", "password_hash")

    mock_response_login = {
        "code": "0000",
        "data": {
            "uid": "user123",
            "accessToken": "access_token_123"
        }
    }

    mock_response_auth = {
        "code": "0000",
        "data": {
            "authCode": "auth_code_123"
        }
    }

    # First call returns set token error, second succeeds
    mock_response_token_error = {
        "result": "fail",
        "error": "set token error.",
        "errno": "100"
    }

    mock_response_token_success = {
        "result": "ok",
        "userId": "user123",
        "token": "final_token",
        "last": "604800000"
    }

    with patch.object(rest_config.session, 'get') as mock_get, \
         patch.object(rest_config.session, 'post') as mock_post:

        login_response = AsyncMock()
        login_response.headers = {"content-type": "application/json"}
        login_response.json = AsyncMock(return_value=mock_response_login)
        login_response.raise_for_status = Mock()

        auth_response = AsyncMock()
        auth_response.headers = {"content-type": "application/json"}
        auth_response.json = AsyncMock(return_value=mock_response_auth)
        auth_response.raise_for_status = Mock()

        mock_get.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=login_response)),
            AsyncMock(__aenter__=AsyncMock(return_value=auth_response))
        ]

        token_error_response = AsyncMock()
        token_error_response.status = HTTPStatus.OK
        token_error_response.json = AsyncMock(return_value=mock_response_token_error)
        token_error_response.raise_for_status = Mock()

        token_success_response = AsyncMock()
        token_success_response.status = HTTPStatus.OK
        token_success_response.json = AsyncMock(return_value=mock_response_token_success)
        token_success_response.raise_for_status = Mock()

        mock_post.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=token_error_response)),
            AsyncMock(__aenter__=AsyncMock(return_value=token_success_response))
        ]

        credentials = await auth_client.login()

        assert credentials.user_id == "user123"
        assert credentials.token == "final_token"
        assert mock_post.call_count == 2


async def test_auth_client_login_china_country(rest_config: RestConfiguration) -> None:
    """Test _AuthClient login for China country."""
    from deebot_client.authentication import _AuthClient

    # Create config for China
    config = create_rest_config(
        rest_config.session,
        device_id="test_device",
        alpha_2_country="CN"
    )

    auth_client = _AuthClient(config, "test@example.com", "password_hash")

    mock_response_login = {
        "code": "0000",
        "data": {
            "uid": "user123",
            "accessToken": "access_token_123"
        }
    }

    mock_response_auth = {
        "code": "0000",
        "data": {
            "authCode": "auth_code_123"
        }
    }

    mock_response_token = {
        "result": "ok",
        "userId": "user123",
        "token": "final_token",
        "last": "604800000"
    }

    with patch.object(config.session, 'get') as mock_get, \
         patch.object(config.session, 'post') as mock_post:

        login_response = AsyncMock()
        login_response.headers = {"content-type": "application/json"}
        login_response.json = AsyncMock(return_value=mock_response_login)
        login_response.raise_for_status = Mock()

        auth_response = AsyncMock()
        auth_response.headers = {"content-type": "application/json"}
        auth_response.json = AsyncMock(return_value=mock_response_auth)
        auth_response.raise_for_status = Mock()

        mock_get.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=login_response)),
            AsyncMock(__aenter__=AsyncMock(return_value=auth_response))
        ]

        token_response = AsyncMock()
        token_response.status = HTTPStatus.OK
        token_response.json = AsyncMock(return_value=mock_response_token)
        token_response.raise_for_status = Mock()

        mock_post.return_value.__aenter__ = AsyncMock(return_value=token_response)

        credentials = await auth_client.login()

        assert credentials.user_id == "user123"
        # Verify the login URL contains "CheckMobile" for China
        assert any("CheckMobile" in str(call) for call in mock_get.call_args_list)
