from __future__ import annotations

import asyncio
import base64
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from aiohttp import ClientSession
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import orjson
import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.exceptions import (
    AuthenticationError,
    DeviceVerificationRequiredError,
    InvalidVerificationCodeError,
)
from deebot_client.models import Credentials

if TYPE_CHECKING:
    from deebot_client.authentication import RestConfiguration


_ACCOUNT_ID = "test@example.com"
_PASSWORD_HASH = "password-hash"  # noqa: S105
_PUBLIC_KEY_CONFIG = "PUBLIC.KEY.CONFIG"


def _mock_response(payload: dict[str, Any], *, status: int = HTTPStatus.OK) -> Any:
    response = Mock()
    response.headers = {}
    response.status = status
    response.raise_for_status = Mock()
    response.json = AsyncMock(return_value=payload)
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    return context_manager


def _rest_config_with_mock_session() -> tuple[RestConfiguration, MagicMock]:
    session = MagicMock(spec=ClientSession)
    return (
        create_rest_config(
            session=cast("ClientSession", session),
            device_id="ABC12345",
            alpha_2_country="US",
            override_rest_url="https://example.com",
        ),
        session,
    )


def _public_key_response(private_key: rsa.RSAPrivateKey) -> dict[str, Any]:
    encoded_key = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode()
    return {
        "code": "0000",
        "data": [
            {
                "key": _PUBLIC_KEY_CONFIG,
                "value": orjson.dumps({"publicKey": encoded_key}).decode(),
            }
        ],
    }


def _decrypt_parameter(
    private_key: rsa.RSAPrivateKey, params: dict[str, Any], parameter: str
) -> str:
    return private_key.decrypt(
        base64.b64decode(params[parameter]), padding.PKCS1v15()
    ).decode()


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


async def test_login_requires_device_verification() -> None:
    config, session = _rest_config_with_mock_session()
    session.get.return_value = _mock_response(
        {
            "code": "1013",
            "msg": "Please update to the latest version to continue.",
            "data": None,
        }
    )
    authenticator = Authenticator(config, _ACCOUNT_ID, _PASSWORD_HASH)

    with pytest.raises(DeviceVerificationRequiredError):
        await authenticator.authenticate()

    url = session.get.call_args.args[0]
    assert "/global_e/1.6.3/google_play/1/user/login" in url


async def test_request_device_verification_code() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    config, session = _rest_config_with_mock_session()
    session.get.side_effect = [
        _mock_response(_public_key_response(private_key)),
        _mock_response({"code": "0000", "data": {"verifyId": "verify-id"}}),
    ]
    authenticator = Authenticator(config, _ACCOUNT_ID, _PASSWORD_HASH)

    await authenticator.request_device_verification_code()

    assert session.get.call_count == 2
    public_key_call, send_code_call = session.get.call_args_list
    assert (
        public_key_call.args[0]
        == "https://example.com/v1/private/us/EN/ABC12345/global_e/3.14.0/google_play/1/common/getConfig"
    )
    assert public_key_call.kwargs["params"]["keys"] == _PUBLIC_KEY_CONFIG
    send_params = send_code_call.kwargs["params"]
    assert _decrypt_parameter(private_key, send_params, "encryptEmail") == _ACCOUNT_ID
    assert send_params["verifyType"] == "EMAIL_VERIFY_DEVICE"
    assert send_params["supportChar"] == "N"
    assert send_params["isForce"] == "N"
    assert send_params["authAppkey"] == "1520391301804"
    assert send_params["authSign"]
    assert send_params["requestId"]
    assert send_params["authTimeZone"] == "GMT-8"


async def test_verify_device_completes_login_and_caches_credentials() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    config, session = _rest_config_with_mock_session()
    session.get.side_effect = [
        _mock_response(_public_key_response(private_key)),
        _mock_response({"code": "0000", "data": {"verifyId": "verify-id"}}),
        _mock_response(
            {
                "code": "0000",
                "data": {"uid": "user-id", "accessToken": "access-token"},
            }
        ),
        _mock_response({"code": "0000", "data": {"authCode": "auth-code"}}),
    ]
    session.post.return_value = _mock_response(
        {
            "result": "ok",
            "userId": "user-id",
            "token": "portal-token",
            "last": 604800000,
        }
    )
    authenticator = Authenticator(config, _ACCOUNT_ID, _PASSWORD_HASH)

    await authenticator.request_device_verification_code()
    credentials = await authenticator.verify_device(" 123456 ")

    assert credentials.token == "portal-token"  # noqa: S105
    assert credentials.user_id == "user-id"
    assert credentials.expires_at > time.time()
    assert await authenticator.authenticate() == credentials
    assert session.get.call_count == 4
    assert session.post.call_count == 1

    verify_call = session.get.call_args_list[2]
    verify_params = verify_call.kwargs["params"]
    assert (
        _decrypt_parameter(private_key, verify_params, "encryptAccount") == _ACCOUNT_ID
    )
    assert verify_params["verifyCode"] == "123456"
    assert verify_params["model"] == "Pixel 7"
    assert verify_params["system"] == "Android 14"
    post_call = session.post.call_args
    assert post_call.args == ("https://example.com/api/users/user.do",)
    assert post_call.kwargs["json"] == {
        "edition": "ECOGLOBLE",
        "userId": "user-id",
        "token": "auth-code",
        "realm": "ecouser.net",
        "resource": "ABC12345",
        "org": "ECOWW",
        "last": "",
        "country": "US",
        "todo": "loginByItToken",
    }
    assert post_call.kwargs["params"] is None
    assert post_call.kwargs["headers"] is None
    await authenticator.teardown()


async def test_verify_device_rejects_invalid_code() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    config, session = _rest_config_with_mock_session()
    session.get.side_effect = [
        _mock_response(_public_key_response(private_key)),
        _mock_response(
            {
                "code": "1012",
                "msg": "Incorrect verification code.",
                "data": None,
            }
        ),
    ]
    authenticator = Authenticator(config, _ACCOUNT_ID, _PASSWORD_HASH)

    with pytest.raises(InvalidVerificationCodeError):
        await authenticator.verify_device("123456")

    session.post.assert_not_called()


async def test_request_device_verification_rejects_invalid_public_key() -> None:
    config, session = _rest_config_with_mock_session()
    session.get.return_value = _mock_response(
        {
            "code": "0000",
            "data": [
                {
                    "key": _PUBLIC_KEY_CONFIG,
                    "value": '{"publicKey":"not-base64"}',
                }
            ],
        }
    )
    authenticator = Authenticator(config, _ACCOUNT_ID, _PASSWORD_HASH)

    with pytest.raises(AuthenticationError, match="Invalid Ecovacs public key"):
        await authenticator.request_device_verification_code()

    session.get.assert_called_once()
