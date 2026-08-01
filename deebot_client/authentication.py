"""Authentication module."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import orjson

from .const import COUNTRY_CHINA, PATH_API_USERS_USER, REALM
from .exceptions import (
    ApiError,
    ApiTimeoutError,
    AuthenticationError,
    DeviceVerificationRequiredError,
    InvalidAuthenticationError,
    InvalidVerificationCodeError,
)
from .logging_filter import get_logger
from .models import Credentials
from .util import cancel, create_task, md5
from .util.continents import get_continent_url_postfix
from .util.countries import get_ecovacs_country

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Mapping


_LOGGER = get_logger(__name__)

_CLIENT_KEY = "1520391301804"
_CLIENT_SECRET = "6c319b2a5cd3e66e39159c2e28f2fce9"  # noqa: S105
_AUTH_CLIENT_KEY = "1520391491841"
_AUTH_CLIENT_SECRET = "77ef58ce3afbe337da74aa8c5ab963a9"  # noqa: S105
_PRIVATE_API_PATH_FORMAT = "/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}/{endpoint}"
_GLOBAL_AUTHCODE_PATH = "/v1/global/auth/getAuthCode"
_PUBLIC_KEY_CONFIG = "PUBLIC.KEY.CONFIG"
_META = {
    "lang": "EN",
    "appCode": "global_e",
    "appVersion": "3.14.0",
    "channel": "google_play",
    "deviceType": "1",
}
_ANDROID_MODEL = "Pixel 7"
_ANDROID_SYSTEM = "Android 14"
MAX_RETRIES = 3


@dataclass(frozen=True, kw_only=True)
class RestConfiguration:
    """Rest configuration."""

    session: ClientSession
    device_id: str
    country: str
    portal_url: str
    login_url: str
    auth_code_url: str


def create_rest_config(
    session: ClientSession,
    *,
    device_id: str,
    alpha_2_country: str,
    override_rest_url: str | None = None,
) -> RestConfiguration:
    """Create configuration."""
    continent_postfix = get_continent_url_postfix(alpha_2_country)
    country = get_ecovacs_country(alpha_2_country)
    if override_rest_url:
        portal_url = login_url = auth_code_url = override_rest_url
    else:
        portal_url = f"https://portal{continent_postfix}.ecouser.net"
        country_url = country.lower()
        tld = "com" if alpha_2_country != COUNTRY_CHINA else country_url
        login_url = f"https://gl-{country_url}-api.ecovacs.{tld}"
        auth_code_url = f"https://gl-{country_url}-openapi.ecovacs.{tld}"

    return RestConfiguration(
        session=session,
        device_id=device_id,
        country=country,
        portal_url=portal_url,
        login_url=login_url,
        auth_code_url=auth_code_url,
    )


_TIMEOUT = ClientTimeout(60)


class _AuthClient:
    """Ecovacs auth client."""

    def __init__(
        self,
        config: RestConfiguration,
        account_id: str,
        password_hash: str,
    ) -> None:
        self._config = config
        self._account_id = account_id
        self._password_hash = password_hash

        self._meta: dict[str, str] = {
            **_META,
            "country": self._config.country.lower(),
            "deviceId": self._config.device_id,
        }
        self._public_key: rsa.RSAPublicKey | None = None

    async def login(self) -> Credentials:
        """Login using username and password."""
        _LOGGER.debug("Start login to EcovacsAPI")
        login_password_resp = await self.__call_login_api(
            self._account_id, self._password_hash
        )
        return await self.__complete_login(
            login_password_resp, "Invalid login response"
        )

    async def request_device_verification_code(self) -> None:
        """Request a one-time email code to verify the configured device ID."""
        encrypted_email = await self.__encrypt_account(self._account_id)
        await self.__call_private_api(
            "user/sendEmailVerifyCode",
            {
                "encryptEmail": encrypted_email,
                "verifyType": "EMAIL_VERIFY_DEVICE",
                "supportChar": "N",
                "isForce": "N",
            },
        )

    async def verify_device(self, verification_code: str) -> Credentials:
        """Verify the configured device ID using a one-time email code."""
        encrypted_account = await self.__encrypt_account(self._account_id)
        response = await self.__call_private_api(
            "user/verifyDevice",
            {
                "encryptAccount": encrypted_account,
                "backUpEmail": "",
                "verifyCode": verification_code.strip(),
                "model": _ANDROID_MODEL,
                "system": _ANDROID_SYSTEM,
            },
        )
        return await self.__complete_login(response, "Invalid verifyDevice response")

    async def __complete_login(self, response: Any, error: str) -> Credentials:
        """Complete login using the Ecovacs user credentials of the response."""
        data = self.__expect_dict(response, error)
        try:
            user_id = str(data["uid"])
            access_token = str(data["accessToken"])
        except KeyError as ex:
            raise AuthenticationError(error) from ex

        auth_code = await self.__call_auth_api(access_token, user_id)

        login_token_resp = await self.__call_login_by_it_token(user_id, auth_code)
        if login_token_resp["userId"] != user_id:
            _LOGGER.debug("Switching to shorter UID")
            user_id = login_token_resp["userId"]

        user_access_token = login_token_resp["token"]
        # last is validity in milliseconds. Usually 7 days
        # we set the expiry at 99% of the validity
        # 604800 = 7 days
        expires_at = int(
            time.time() + int(login_token_resp.get("last", 604800)) / 1000 * 0.99
        )

        _LOGGER.debug("Login to EcovacsAPI successfully")
        return Credentials(
            token=user_access_token,
            user_id=user_id,
            expires_at=expires_at,
        )

    async def __do_auth_response(self, url: str, params: dict[str, Any]) -> Any:
        async with self._config.session.get(
            url, params=params, timeout=_TIMEOUT
        ) as res:
            res.raise_for_status()

            # ecovacs returns a json but content_type header is set to text
            content_type = res.headers.get(hdrs.CONTENT_TYPE, "").lower()
            json = await res.json(content_type=content_type)
            if not isinstance(json, dict):
                raise AuthenticationError("Invalid authentication response")
            _LOGGER.debug("got %s", json)
            code = json.get("code")
            # TODO better error handling
            if code == "0000":
                return json.get("data")
            message = json.get("msg", "")
            if code in ["1005", "1010"]:
                raise InvalidAuthenticationError(message)
            if code == "1012":
                raise InvalidVerificationCodeError(message)
            if code == "1013":
                raise DeviceVerificationRequiredError(message)

            _LOGGER.error("call to %s failed with %s", url, json)
            msg = f"failure code {code} ({message}) for call {url}"
            raise AuthenticationError(msg)

    @staticmethod
    def __expect_dict(response: Any, error: str) -> dict[str, Any]:
        """Verify that the api returned an object."""
        if not isinstance(response, dict):
            raise AuthenticationError(error)
        return response

    async def __call_login_api(self, account_id: str, password_hash: str) -> Any:
        _LOGGER.debug("calling login api")
        endpoint = "user/login"
        if self._config.country == COUNTRY_CHINA:
            endpoint += "CheckMobile"

        return await self.__call_private_api(
            endpoint, {"account": account_id, "password": password_hash}
        )

    async def __call_private_api(
        self, endpoint: str, params: dict[str, str | int]
    ) -> Any:
        """Call a signed private authentication API endpoint."""
        url = urljoin(
            self._config.login_url,
            _PRIVATE_API_PATH_FORMAT.format(endpoint=endpoint, **self._meta),
        )
        return await self.__do_auth_response(
            url,
            self.__sign(
                {**params, **self.__request_metadata()},
                self._meta,
                _CLIENT_KEY,
                _CLIENT_SECRET,
            ),
        )

    @staticmethod
    def __request_metadata() -> dict[str, str | int]:
        now = time.time()
        return {
            "requestId": md5(str(now)),
            "authTimespan": int(now * 1000),
            "authTimeZone": "GMT-8",
        }

    async def __get_public_key(self) -> rsa.RSAPublicKey:
        # The key is the same for all accounts, therefore we cache it for the
        # lifetime of the client
        if self._public_key is not None:
            return self._public_key

        response = await self.__call_private_api(
            "common/getConfig", {"keys": _PUBLIC_KEY_CONFIG}
        )
        if not isinstance(response, list):
            raise AuthenticationError("Invalid public key configuration response")

        for entry in response:
            if (
                isinstance(entry, dict)
                and entry.get("key") == _PUBLIC_KEY_CONFIG
                and isinstance(value := entry.get("value"), str)
            ):
                self._public_key = self.__load_public_key(value)
                return self._public_key

        raise AuthenticationError("Ecovacs public key configuration is missing")

    @staticmethod
    def __load_public_key(config_value: str) -> rsa.RSAPublicKey:
        """Load the public key from the configuration value."""
        try:
            encoded_key = orjson.loads(config_value)["publicKey"]
        except (KeyError, TypeError, orjson.JSONDecodeError) as ex:
            raise AuthenticationError("Invalid Ecovacs public key") from ex
        if not isinstance(encoded_key, str):
            raise AuthenticationError("Invalid Ecovacs public key")

        try:
            # base64 and DER errors are both a ValueError
            key = serialization.load_der_public_key(
                base64.b64decode(encoded_key, validate=True)
            )
        except ValueError as ex:
            raise AuthenticationError("Invalid Ecovacs public key") from ex

        if not isinstance(key, rsa.RSAPublicKey):
            raise AuthenticationError("Ecovacs public key is not an RSA key")
        return key

    async def __encrypt_account(self, account: str) -> str:
        public_key = await self.__get_public_key()
        # PKCS1v15 padding is required by the Ecovacs api
        encrypted = public_key.encrypt(account.encode(), padding.PKCS1v15())
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def __sign(
        params: dict[str, str | int],
        additional_sign_params: Mapping[str, str | int],
        key: str,
        secret: str,
    ) -> dict[str, str | int]:
        sign_data: dict[str, str | int] = {**additional_sign_params, **params}
        sign_on_text = (
            key
            + "".join([k + "=" + str(sign_data[k]) for k in sorted(sign_data.keys())])
            + secret
        )
        params["authSign"] = md5(sign_on_text)
        params["authAppkey"] = key
        return params

    async def __call_auth_api(self, access_token: str, user_id: str) -> str:
        _LOGGER.debug("calling auth api")
        params: dict[str, str | int] = {
            "uid": user_id,
            "accessToken": access_token,
            "bizType": "ECOVACS_IOT",
            "deviceId": self._meta["deviceId"],
            "authTimespan": int(time.time() * 1000),
        }

        url = urljoin(self._config.auth_code_url, _GLOBAL_AUTHCODE_PATH)

        response = await self.__do_auth_response(
            url,
            self.__sign(
                params, {"openId": "global"}, _AUTH_CLIENT_KEY, _AUTH_CLIENT_SECRET
            ),
        )
        res = self.__expect_dict(response, "Invalid auth code response")
        return str(res["authCode"])

    async def __call_login_by_it_token(
        self, user_id: str, auth_code: str
    ) -> dict[str, str]:
        data = {
            "edition": "ECOGLOBLE",
            "userId": user_id,
            "token": auth_code,
            "realm": REALM,
            "resource": self._config.device_id,
            "org": "ECOWW" if self._config.country != COUNTRY_CHINA else "ECOCN",
            "last": "",
            "country": self._config.country
            if self._config.country != COUNTRY_CHINA
            else "Chinese",
            "todo": "loginByItToken",
        }

        for i in range(3):
            resp = await self.post(PATH_API_USERS_USER, data)
            if resp["result"] == "ok":
                return resp
            if resp["result"] == "fail" and resp["error"] == "set token error.":
                # If it is a set token error try again
                _LOGGER.warning("loginByItToken set token error, attempt %d/3", i + 2)
                continue

            _LOGGER.error("call to %s failed with %s", PATH_API_USERS_USER, resp)
            msg = f"failure {resp['error']} ({resp['errno']}) for call {PATH_API_USERS_USER}"
            raise AuthenticationError(msg)

        raise AuthenticationError("failed to login with token")

    async def post(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        credentials: Credentials | None = None,
    ) -> dict[str, Any]:
        """Perform a post request."""
        url = urljoin(self._config.portal_url, "api/" + path)
        logger_request_params = f"url={url}, params={query_params}, json={json}"

        if credentials is not None:
            json.update(
                {
                    "auth": {
                        "with": "users",
                        "userid": credentials.user_id,
                        "realm": REALM,
                        "token": credentials.token,
                        "resource": self._config.device_id,
                    }
                }
            )

        for i in range(MAX_RETRIES):
            _LOGGER.debug(
                "Calling api(%d/%d): %s",
                i + 1,
                MAX_RETRIES,
                logger_request_params,
            )

            try:
                async with self._config.session.post(
                    url,
                    json=json,
                    params=query_params,
                    headers=headers,
                    timeout=_TIMEOUT,
                ) as res:
                    res.raise_for_status()

                    if res.status == HTTPStatus.OK:
                        response_data: dict[str, Any] = await res.json()
                        _LOGGER.debug(
                            "Success calling api %s, response=%s",
                            logger_request_params,
                            response_data,
                        )
                        return response_data

                    _LOGGER.debug(
                        "Error calling api %s, response=%s", logger_request_params, res
                    )
                    raise ApiError("Request failed") from ClientResponseError(
                        res.request_info,
                        res.history,
                        status=res.status,
                        message=str(res.reason),
                        headers=res.headers,
                    )
            except TimeoutError as ex:
                _LOGGER.debug("Timeout (%d) reached on path: %s", _TIMEOUT, path)
                raise ApiTimeoutError(path=path, timeout=_TIMEOUT) from ex
            except ClientResponseError as ex:
                _LOGGER.debug("Error: %s", logger_request_params, exc_info=True)
                if ex.status == HTTPStatus.BAD_GATEWAY:
                    seconds_to_sleep = 10
                    _LOGGER.info(
                        "Retry calling API due 502: Unfortunately the ecovacs api is unreliable. Retrying in %d seconds",
                        seconds_to_sleep,
                    )

                    await asyncio.sleep(seconds_to_sleep)
                    continue

                raise ApiError from ex

        raise ApiError("Unknown error occurred")


class Authenticator:
    """Authenticator."""

    def __init__(
        self,
        config: RestConfiguration,
        account_id: str,
        password_hash: str,
    ) -> None:
        self._auth_client = _AuthClient(
            config,
            account_id,
            password_hash,
        )

        self._lock = asyncio.Lock()
        self._on_credentials_changed: set[
            Callable[[Credentials], Coroutine[Any, Any, None]]
        ] = set()
        self._credentials: Credentials | None = None
        self._refresh_handle: asyncio.TimerHandle | None = None
        self._tasks: set[asyncio.Future[Any]] = set()

    async def authenticate(self, *, force: bool = False) -> Credentials:
        """Authenticate on ecovacs servers."""
        async with self._lock:
            credentials = self._credentials
            if credentials is None or force or credentials.expires_at < time.time():
                _LOGGER.debug("Performing login")
                credentials = await self._auth_client.login()
                self._set_credentials(credentials)

            return credentials

    async def request_device_verification_code(self) -> None:
        """Request a one-time email code to verify the configured device ID."""
        await self._auth_client.request_device_verification_code()

    async def verify_device(self, verification_code: str) -> Credentials:
        """Verify the configured device ID using a one-time email code."""
        async with self._lock:
            credentials = await self._auth_client.verify_device(verification_code)
            self._set_credentials(credentials)
            return credentials

    def _set_credentials(self, credentials: Credentials) -> None:
        """Store credentials and schedule their refresh."""
        self._credentials = credentials
        self._cancel_refresh_task()
        self._create_refresh_task(credentials)

        for on_changed in self._on_credentials_changed:
            create_task(self._tasks, on_changed(credentials))

    def subscribe(
        self, callback: Callable[[Credentials], Coroutine[Any, Any, None]]
    ) -> Callable[[], None]:
        """Add callback on new credentials and return subscribe callback."""

        def unsubscribe() -> None:
            self._on_credentials_changed.remove(callback)

        self._on_credentials_changed.add(callback)
        return unsubscribe

    async def post_authenticated(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated post request."""
        return await self._auth_client.post(
            path,
            json,
            query_params=query_params,
            headers=headers,
            credentials=await self.authenticate(),
        )

    async def teardown(self) -> None:
        """Teardown authenticator."""
        self._cancel_refresh_task()
        await cancel(self._tasks)

    def _cancel_refresh_task(self) -> None:
        if self._refresh_handle and not self._refresh_handle.cancelled():
            self._refresh_handle.cancel()

    def _create_refresh_task(self, credentials: Credentials) -> None:
        # refresh at 99% of validity
        def refresh() -> None:
            _LOGGER.debug("Refresh token")

            async def async_refresh() -> None:
                try:
                    await self.authenticate(force=True)
                except Exception:
                    _LOGGER.exception("An exception occurred during refreshing token")

            create_task(self._tasks, async_refresh())
            self._refresh_handle = None

        validity = (credentials.expires_at - time.time()) * 0.99

        self._refresh_handle = asyncio.get_event_loop().call_later(validity, refresh)
