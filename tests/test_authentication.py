from __future__ import annotations

import asyncio
import base64
from collections import defaultdict
from dataclasses import dataclass
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

from aiohttp import ClientSession, hdrs, web
from aiohttp.test_utils import TestServer
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
import orjson
import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.exceptions import (
    AuthenticationError,
    DeviceVerificationRequiredError,
    InvalidAuthenticationError,
    InvalidVerificationCodeError,
)
from deebot_client.models import AccountCredentials, Credentials

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from deebot_client.authentication import RestConfiguration


_ACCOUNT_ID = "test@example.com"
_PASSWORD_HASH = "password-hash"  # noqa: S105
_DEVICE_ID = "ABC12345"
_PUBLIC_KEY_CONFIG = "PUBLIC.KEY.CONFIG"


@dataclass(frozen=True, kw_only=True)
class _RecordedRequest:
    """Request received by the fake Ecovacs api."""

    path: str
    query: dict[str, str]
    json: dict[str, Any] | None


class _FakeEcovacsApi:
    """Fake Ecovacs api, which answers with the configured payload per endpoint.

    Requests are routed by the last segment of their path, so a test only needs
    to configure the endpoints it cares about. Requesting an endpoint without a
    payload fails with a 404 instead of silently succeeding.
    """

    def __init__(self, responses: dict[str, Any]) -> None:
        self.url = ""
        self.responses = responses
        self.requests: defaultdict[str, list[_RecordedRequest]] = defaultdict(list)
        self._server: TestServer | None = None

    async def start(self) -> None:
        """Start the api."""
        app = web.Application()
        app.router.add_route("*", "/{path:.*}", self._handle)
        self._server = TestServer(app)
        # the access log would leak the credentials of the query into the log
        await self._server.start_server(access_log=None)
        self.url = str(self._server.make_url("")).rstrip("/")

    async def stop(self) -> None:
        """Stop the api."""
        if self._server is not None:
            await self._server.close()

    async def _handle(self, request: web.Request) -> web.StreamResponse:
        endpoint = request.path.rpartition("/")[2]
        self.requests[endpoint].append(
            _RecordedRequest(
                path=request.path,
                query=dict(request.query),
                json=orjson.loads(await request.read())
                if request.can_read_body
                else None,
            )
        )

        if endpoint not in self.responses:
            raise web.HTTPNotFound
        body = orjson.dumps(self.responses[endpoint])

        if request.method == hdrs.METH_POST:
            return web.Response(body=body, content_type="application/json")
        # the auth api returns a json, but declares it as text
        return web.Response(body=body, content_type="text/plain", charset="utf-8")


def _key_config(value: Any) -> dict[str, Any]:
    return {"key": _PUBLIC_KEY_CONFIG, "value": value}


def _public_key_config(
    public_key: rsa.RSAPublicKey | ec.EllipticCurvePublicKey,
) -> str:
    """Return the public key configuration value as sent by the api."""
    encoded_key = base64.b64encode(
        public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode()
    return orjson.dumps({"publicKey": encoded_key}).decode()


def _successful_responses(private_key: rsa.RSAPrivateKey) -> dict[str, Any]:
    """Return the responses of a successful login and device verification."""
    user = {"code": "0000", "data": {"uid": "user-id", "accessToken": "access-token"}}
    return {
        "login": user,
        "loginCheckMobile": user,
        "verifyDevice": user,
        "sendEmailVerifyCode": {"code": "0000", "data": {"verifyId": "verify-id"}},
        "getAuthCode": {"code": "0000", "data": {"authCode": "auth-code"}},
        "getConfig": {
            "code": "0000",
            "data": [_key_config(_public_key_config(private_key.public_key()))],
        },
        "user.do": {
            "result": "ok",
            "userId": "user-id",
            "token": "portal-token",
            "last": 604800000,
        },
    }


@pytest.fixture(scope="session")
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
async def api(private_key: rsa.RSAPrivateKey) -> AsyncGenerator[_FakeEcovacsApi]:
    api = _FakeEcovacsApi(_successful_responses(private_key))
    await api.start()
    yield api
    await api.stop()


@pytest.fixture
def alpha_2_country() -> str:
    return "US"


@pytest.fixture
async def auth(
    session: ClientSession, api: _FakeEcovacsApi, alpha_2_country: str
) -> AsyncGenerator[Authenticator]:
    authenticator = Authenticator(
        create_rest_config(
            session=session,
            device_id=_DEVICE_ID,
            alpha_2_country=alpha_2_country,
            override_rest_url=api.url,
        ),
        _ACCOUNT_ID,
        _PASSWORD_HASH,
    )
    yield authenticator
    await authenticator.teardown()


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


async def test_login_completes_login_and_sanitizes_response_log(
    api: _FakeEcovacsApi,
    auth: Authenticator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    api.responses["user.do"]["userId"] = "short-user-id"

    credentials = await auth.authenticate()

    assert credentials.token == "portal-token"  # noqa: S105
    assert credentials.user_id == "short-user-id"
    assert credentials.expires_at > time.time()
    assert "'accessToken': '[REMOVED]'" in caplog.text
    assert "access-token" not in caplog.text

    request = api.requests["login"][0]
    assert request.path == (
        f"/v1/private/us/EN/{_DEVICE_ID}/global_e/3.14.0/google_play/1/user/login"
    )
    assert request.query["account"] == _ACCOUNT_ID
    assert request.query["password"] == _PASSWORD_HASH
    assert api.requests["user.do"][0].json == {
        "edition": "ECOGLOBLE",
        "userId": "user-id",
        "token": "auth-code",
        "realm": "ecouser.net",
        "resource": _DEVICE_ID,
        "org": "ECOWW",
        "last": "",
        "country": "US",
        "todo": "loginByItToken",
    }


@pytest.mark.parametrize("alpha_2_country", ["CN"])
async def test_login_china_uses_check_mobile_endpoint(
    api: _FakeEcovacsApi, auth: Authenticator
) -> None:
    credentials = await auth.authenticate()

    assert credentials.token == "portal-token"  # noqa: S105
    assert api.requests["loginCheckMobile"][0].path == (
        f"/v1/private/cn/EN/{_DEVICE_ID}/global_e/3.14.0/google_play/1/user/loginCheckMobile"
    )
    portal_json = api.requests["user.do"][0].json
    assert portal_json is not None
    assert portal_json["org"] == "ECOCN"
    assert portal_json["country"] == "Chinese"


@pytest.mark.parametrize(
    ("code", "error_type"),
    [
        ("1005", InvalidAuthenticationError),
        ("1010", InvalidAuthenticationError),
        ("1012", InvalidVerificationCodeError),
        ("1013", DeviceVerificationRequiredError),
    ],
)
async def test_auth_response_error_codes(
    api: _FakeEcovacsApi,
    auth: Authenticator,
    code: str,
    error_type: type[AuthenticationError],
) -> None:
    api.responses["login"] = {"code": code, "msg": f"error {code}", "data": None}

    with pytest.raises(error_type, match=f"error {code}"):
        await auth.authenticate()

    assert list(api.requests) == ["login"]


@pytest.mark.parametrize(
    ("response", "error"),
    [
        ({"code": "9999", "msg": "Boom"}, r"failure code 9999 \(Boom\)"),
        # the api does not always include a message
        ({"code": "9999"}, r"failure code 9999 \(\)"),
        ([], "Invalid authentication response"),
        ({"code": "0000", "data": []}, "Invalid login response"),
        ({"code": "0000", "data": {"uid": "user-id"}}, "Invalid login response"),
    ],
)
async def test_login_rejects_invalid_response(
    api: _FakeEcovacsApi, auth: Authenticator, response: Any, error: str
) -> None:
    api.responses["login"] = response

    with pytest.raises(AuthenticationError, match=error):
        await auth.authenticate()


async def test_login_rejects_invalid_auth_code_response(
    api: _FakeEcovacsApi, auth: Authenticator
) -> None:
    api.responses["getAuthCode"] = {"code": "0000", "data": []}

    with pytest.raises(AuthenticationError, match="Invalid auth code response"):
        await auth.authenticate()


async def test_request_device_verification_code(
    api: _FakeEcovacsApi, auth: Authenticator, private_key: rsa.RSAPrivateKey
) -> None:
    await auth.request_device_verification_code()

    assert api.requests["getConfig"][0].query["keys"] == _PUBLIC_KEY_CONFIG
    params = api.requests["sendEmailVerifyCode"][0].query
    assert _decrypt_parameter(private_key, params, "encryptEmail") == _ACCOUNT_ID
    assert params["verifyType"] == "EMAIL_VERIFY_DEVICE"
    assert params["supportChar"] == "N"
    assert params["isForce"] == "N"
    assert params["authAppkey"] == "1520391301804"
    assert params["authSign"]
    assert params["requestId"]
    assert params["authTimespan"]
    assert params["authTimeZone"] == "GMT-8"


async def test_public_key_is_only_requested_once(
    api: _FakeEcovacsApi, auth: Authenticator
) -> None:
    await auth.request_device_verification_code()
    await auth.request_device_verification_code()

    assert len(api.requests["getConfig"]) == 1
    assert len(api.requests["sendEmailVerifyCode"]) == 2


async def test_verify_device_completes_login_and_caches_credentials(
    api: _FakeEcovacsApi, auth: Authenticator, private_key: rsa.RSAPrivateKey
) -> None:
    await auth.request_device_verification_code()
    credentials = await auth.verify_device(" 123456 ")

    assert credentials.token == "portal-token"  # noqa: S105
    assert credentials.user_id == "user-id"
    assert credentials.expires_at > time.time()
    # the credentials are cached, therefore no login is performed
    assert await auth.authenticate() == credentials
    assert "login" not in api.requests

    params = api.requests["verifyDevice"][0].query
    assert _decrypt_parameter(private_key, params, "encryptAccount") == _ACCOUNT_ID
    assert params["verifyCode"] == "123456"
    assert params["model"] == "Pixel 7"
    assert params["system"] == "Android 14"
    assert params["backUpEmail"] == ""


async def test_verify_device_notifies_subscribers(auth: Authenticator) -> None:
    changed: asyncio.Queue[Credentials] = asyncio.Queue()
    auth.subscribe(changed.put)

    credentials = await auth.verify_device("123456")

    async with asyncio.timeout(0.1):
        assert await changed.get() == credentials


async def test_verify_device_rejects_invalid_code(
    api: _FakeEcovacsApi, auth: Authenticator
) -> None:
    api.responses["verifyDevice"] = {"code": "1012", "msg": "Wrong code", "data": None}

    with pytest.raises(InvalidVerificationCodeError):
        await auth.verify_device("123456")

    assert list(api.requests) == ["getConfig", "verifyDevice"]


@pytest.mark.parametrize("response_data", [[], {"uid": "user-id"}])
async def test_verify_device_rejects_invalid_response(
    api: _FakeEcovacsApi, auth: Authenticator, response_data: object
) -> None:
    api.responses["verifyDevice"] = {"code": "0000", "data": response_data}

    with pytest.raises(AuthenticationError, match="Invalid verifyDevice response"):
        await auth.verify_device("123456")


@pytest.mark.parametrize(
    ("response_data", "error"),
    [
        ({}, "Invalid public key configuration response"),
        ([], "public key configuration is missing"),
        ([_key_config(None)], "public key configuration is missing"),
        ([{"key": "OTHER", "value": "{}"}], "public key configuration is missing"),
        ([_key_config("not-json")], "Invalid Ecovacs public key"),
        ([_key_config('{"publicKey":123}')], "Invalid Ecovacs public key"),
        ([_key_config('{"publicKey":"bm90LWEta2V5"}')], "Invalid Ecovacs public key"),
    ],
)
async def test_request_device_verification_rejects_invalid_public_key(
    api: _FakeEcovacsApi, auth: Authenticator, response_data: object, error: str
) -> None:
    api.responses["getConfig"] = {"code": "0000", "data": response_data}

    with pytest.raises(AuthenticationError, match=error):
        await auth.request_device_verification_code()

    assert list(api.requests) == ["getConfig"]


async def test_request_device_verification_rejects_non_rsa_public_key(
    api: _FakeEcovacsApi, auth: Authenticator
) -> None:
    public_key = ec.generate_private_key(ec.SECP256R1()).public_key()
    api.responses["getConfig"]["data"] = [_key_config(_public_key_config(public_key))]

    with pytest.raises(AuthenticationError, match="public key is not an RSA key"):
        await auth.request_device_verification_code()


async def test_request_device_verification_skips_invalid_duplicate_config(
    api: _FakeEcovacsApi, auth: Authenticator
) -> None:
    api.responses["getConfig"]["data"].insert(0, _key_config(None))

    await auth.request_device_verification_code()

    assert len(api.requests["sendEmailVerifyCode"]) == 1


async def test_authenticate_prefers_token_based_renewal(
    session: ClientSession, api: _FakeEcovacsApi
) -> None:
    """A seeded access token mints portal credentials without a password login."""
    authenticator = Authenticator(
        create_rest_config(
            session=session,
            device_id=_DEVICE_ID,
            alpha_2_country="US",
            override_rest_url=api.url,
        ),
        _ACCOUNT_ID,
        _PASSWORD_HASH,
        account_credentials=AccountCredentials(
            access_token="access-token",  # noqa: S106
            user_id="user-id",
        ),
    )
    try:
        credentials = await authenticator.authenticate()

        assert credentials.token == "portal-token"  # noqa: S105
        assert credentials.user_id == "user-id"
        assert "login" not in api.requests
        assert api.requests["getAuthCode"][0].query["accessToken"] == "access-token"
        assert api.requests["user.do"][0].json is not None
    finally:
        await authenticator.teardown()


async def test_authenticate_falls_back_to_password_login(
    rest_config: RestConfiguration,
) -> None:
    """An expired access token falls back to the password login."""
    with patch("deebot_client.authentication._AuthClient", spec_set=True) as api_client:
        login_with_account_mock: AsyncMock = api_client.return_value.login_with_account
        login_with_account_mock.side_effect = AuthenticationError("token expired")
        login_mock: AsyncMock = api_client.return_value.login
        login_mock.return_value = Credentials(
            "token", "user_id", int(time.time() + 123456789)
        )
        account = AccountCredentials(access_token="expired", user_id="user_id")  # noqa: S106
        authenticator = Authenticator(
            rest_config, "test", "test", account_credentials=account
        )

        assert (await authenticator.authenticate()) == login_mock.return_value
        login_with_account_mock.assert_awaited_once_with(account)
        login_mock.assert_awaited_once()


async def test_login_stores_and_notifies_account_credentials(
    auth: Authenticator,
) -> None:
    """A password login stores the account credentials and notifies subscribers."""
    changed: asyncio.Queue[AccountCredentials] = asyncio.Queue()
    auth.subscribe_account_credentials(changed.put)
    assert auth.account_credentials is None

    await auth.authenticate()

    account = AccountCredentials(access_token="access-token", user_id="user-id")  # noqa: S106
    assert auth.account_credentials == account
    async with asyncio.timeout(0.1):
        assert await changed.get() == account


async def test_verify_device_stores_account_credentials(auth: Authenticator) -> None:
    """A device verification stores the account credentials for later renewals."""
    await auth.verify_device("123456")

    assert auth.account_credentials == AccountCredentials(
        access_token="access-token",  # noqa: S106
        user_id="user-id",
    )
