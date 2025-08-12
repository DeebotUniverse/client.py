"""Authentication module."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs

from .const import (
    COUNTRY_CHINA,
    PATH_API_IOT_CONTROL,
    PATH_API_IOT_DEVMANAGER,
    PATH_API_ISSUE_NEW_PERMISSION,
    PATH_API_USERS_USER,
    REALM,
    REQUEST_HEADERS,
)
from .exceptions import (
    ApiError,
    ApiTimeoutError,
    AuthenticationError,
    InvalidAuthenticationError,
)
from .logging_filter import get_logger
from .models import ApiDeviceInfo, Credentials
from .util import cancel, create_task, md5
from .util.continents import get_continent_url_postfix
from .util.countries import get_ecovacs_country

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Mapping

    from multidict import istr

    from .command import Command


_LOGGER = get_logger(__name__)

_CLIENT_KEY = "1520391301804"
_CLIENT_SECRET = "6c319b2a5cd3e66e39159c2e28f2fce9"  # noqa: S105
_AUTH_CLIENT_KEY = "1520391491841"
_AUTH_CLIENT_SECRET = "77ef58ce3afbe337da74aa8c5ab963a9"  # noqa: S105
_USER_LOGIN_PATH_FORMAT = "/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}/user/login"
_GLOBAL_AUTHCODE_PATH = "/v1/global/auth/getAuthCode"
_META = {
    "lang": "EN",
    "appCode": "global_e",
    "appVersion": "1.6.3",
    "channel": "google_play",
    "deviceType": "1",
}
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
    api_base_url: str


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
        portal_url = login_url = auth_code_url = api_base_url = override_rest_url
    else:
        portal_url = f"https://portal{continent_postfix}.ecouser.net"
        country_url = country.lower()
        tld = "com" if alpha_2_country != COUNTRY_CHINA else country_url
        login_url = f"https://gl-{country_url}-api.ecovacs.{tld}"
        auth_code_url = f"https://gl-{country_url}-openapi.ecovacs.{tld}"
        api_base_url = f"https://api-base.dc{continent_postfix}.ww.ecouser.net"

    return RestConfiguration(
        session=session,
        device_id=device_id,
        country=country,
        portal_url=portal_url,
        login_url=login_url,
        auth_code_url=auth_code_url,
        api_base_url=api_base_url,
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
        self._api_users_url = urljoin(
            self._config.portal_url, "api/" + PATH_API_USERS_USER
        )

    async def login(self) -> Credentials:
        """Login using username and password."""
        _LOGGER.debug("Start login to EcovacsAPI")
        login_password_resp = await self.__call_login_api(
            self._account_id, self._password_hash
        )
        user_id = login_password_resp["uid"]

        auth_code = await self.__call_auth_api(
            login_password_resp["accessToken"], user_id
        )

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

    async def __do_auth_response(
        self, url: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._config.session.get(
            url, params=params, timeout=_TIMEOUT
        ) as res:
            res.raise_for_status()

            # ecovacs returns a json but content_type header is set to text
            content_type = res.headers.get(hdrs.CONTENT_TYPE, "").lower()
            json = await res.json(content_type=content_type)
            _LOGGER.debug("got %s", json)
            # TODO better error handling
            if json["code"] == "0000":
                data: dict[str, Any] = json["data"]
                return data
            if json["code"] in ["1005", "1010"]:
                raise InvalidAuthenticationError

            _LOGGER.error("call to %s failed with %s", url, json)
            msg = f"failure code {json['code']} ({json['msg']}) for call {url}"
            raise AuthenticationError(msg)

    async def __call_login_api(
        self, account_id: str, password_hash: str
    ) -> dict[str, Any]:
        _LOGGER.debug("calling login api")
        params: dict[str, str | int] = {
            "account": account_id,
            "password": password_hash,
            "requestId": md5(str(time.time())),
            "authTimespan": int(time.time() * 1000),
            "authTimeZone": "GMT-8",
        }

        url = urljoin(
            self._config.login_url, _USER_LOGIN_PATH_FORMAT.format(**self._meta)
        )

        if self._config.country == COUNTRY_CHINA:
            url += "CheckMobile"

        return await self.__do_auth_response(
            url, self.__sign(params, self._meta, _CLIENT_KEY, _CLIENT_SECRET)
        )

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

        res = await self.__do_auth_response(
            url,
            self.__sign(
                params, {"openId": "global"}, _AUTH_CLIENT_KEY, _AUTH_CLIENT_SECRET
            ),
        )
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
            resp = await _post(self._config.session, self._api_users_url, data)
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


async def _post(
    session: ClientSession,
    url: str,
    json: dict[str | istr, Any],
    *,
    query_params: dict[str, Any] | None = None,
    headers: dict[istr, str] | None = None,
    expected_content_type: str = "application/json",
) -> dict[str, Any]:
    """Perform a post request."""
    logger_request_params = f"url={url}, params={query_params}, json={json}"

    for i in range(MAX_RETRIES):
        _LOGGER.debug(
            "Calling api(%d/%d): %s",
            i + 1,
            MAX_RETRIES,
            logger_request_params,
        )

        try:
            async with session.post(
                url,
                json=json,
                params=query_params,
                headers=headers,
                timeout=_TIMEOUT,
            ) as res:
                res.raise_for_status()

                if res.status == HTTPStatus.OK:
                    response_data: dict[str, Any] = await res.json(
                        content_type=expected_content_type
                    )
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
            _LOGGER.debug("Timeout (%d) reached on path: %s", _TIMEOUT, url)
            raise ApiTimeoutError(path=url, timeout=_TIMEOUT) from ex
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


class Authenticator(ABC):
    """Base authenticator."""

    def __init__(
        self,
        credentials_fn: Callable[[], Awaitable[Credentials]],
    ) -> None:
        self._credentials_fn = credentials_fn

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
            if (
                self._credentials is None
                or force
                or self._credentials.expires_at < time.time()
            ):
                _LOGGER.debug("Performing login")
                self._cancel_refresh_task()
                self._credentials = await self._credentials_fn()
                self._create_refresh_task(self._credentials)

                for on_changed in self._on_credentials_changed:
                    create_task(self._tasks, on_changed(self._credentials))

            return self._credentials

    def subscribe(
        self, callback: Callable[[Credentials], Coroutine[Any, Any, None]]
    ) -> Callable[[], None]:
        """Add callback on new credentials and return subscribe callback."""

        def unsubscribe() -> None:
            self._on_credentials_changed.remove(callback)

        self._on_credentials_changed.add(callback)
        return unsubscribe

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

    @abstractmethod
    async def post_authenticated(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[istr, str] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated post request."""

    @abstractmethod
    async def execute_command_request(
        self, command: Command, device_info: ApiDeviceInfo
    ) -> dict[str, Any]:
        """Execute a command request."""


class UserAuthenticator(Authenticator):
    """User authenticator."""

    def __init__(
        self, config: RestConfiguration, account_id: str, password_hash: str
    ) -> None:
        self._config = config
        auth_client = _AuthClient(config, account_id, password_hash)

        super().__init__(auth_client.login)

    async def post_authenticated(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[istr, str] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated post request."""
        credentials = await self.authenticate()
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

        url = urljoin(self._config.portal_url, "api/" + path)
        return await _post(
            self._config.session,
            url,
            json,
            query_params=query_params,
            headers=headers,
        )

    async def execute_command_request(
        self, command: Command, device_info: ApiDeviceInfo
    ) -> dict[str, Any]:
        """Execute a command request."""
        credentials = await self.authenticate()

        payload = {
            "cmdName": command.NAME,
            "payload": command.get_payload(),
            "payloadType": command.DATA_TYPE.value,
            "td": "q",
            "toId": device_info["did"],
            "toRes": device_info["resource"],
            "toType": device_info["class"],
        }

        query_params = {
            "mid": payload["toType"],
            "did": payload["toId"],
            "td": payload["td"],
            "u": credentials.user_id,
            "cv": "1.67.3",
            "t": "a",
            "av": "1.3.1",
        }
        return await self.post_authenticated(
            PATH_API_IOT_DEVMANAGER,
            payload,
            query_params=query_params,
            headers=REQUEST_HEADERS,
        )


class DeviceAuthenticator(Authenticator):
    """Device authenticator."""

    def __init__(
        self,
        config: RestConfiguration,
        user_authenticator: UserAuthenticator,
        device_info: ApiDeviceInfo,
    ) -> None:
        self._config = config
        self._user_authenticator = user_authenticator
        self._device_info = device_info

        super().__init__(self._get_device_token)

    async def _get_device_token(self) -> Credentials:
        """Get access token for a device."""
        user_credentials = await self._user_authenticator.authenticate()
        validity = 600
        expires_at = int(time.time() + validity)
        perm_payload = {
            "acl": [
                {
                    "policy": [
                        {
                            "obj": [
                                f"Endpoint:{self._device_info['class']}:{self._device_info['did']}"
                            ],
                            "perms": ["Control"],
                        }
                    ],
                    "svc": "dim",
                }
            ],
            "exp": validity,
            "sub": user_credentials.user_id,
        }
        url = urljoin(self._config.api_base_url, "api/" + PATH_API_ISSUE_NEW_PERMISSION)
        response = await _post(
            self._config.session,
            url,
            perm_payload,
            headers={
                hdrs.CONTENT_TYPE: "application/json",
                hdrs.AUTHORIZATION: f"Bearer {user_credentials.token}",
            },
        )
        return Credentials(
            response["data"]["data"]["token"],
            user_credentials.user_id,
            expires_at,
        )

    async def post_authenticated(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[istr, str] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated post request."""
        return await self._user_authenticator.post_authenticated(
            path,
            json,
            query_params=query_params,
            headers=headers,
        )

    async def execute_command_request(
        self, command: Command, device_info: ApiDeviceInfo
    ) -> dict[str, Any]:
        """Execute a command request."""
        body = {
            "header": {
                "channel": "Android",
                "m": "request",
                "pri": 2,
                "ver": "0.0.22",
                "tzm": 60,
                "tzc": "Europe/London",
            },
            "payload": command.get_payload(),
        }

        credentials = await self.authenticate()
        query_params = {
            "fmt": command.DATA_TYPE.value,
            "ct": "q",
            "eid": device_info["did"],
            "er": device_info["resource"],
            "et": device_info["class"],
            "apn": command.NAME,
            "si": device_info[
                "resource"
            ],  # new http param si (some random id which matches request header X-ECO-REQUEST-ID)
        }

        headers = {
            **REQUEST_HEADERS,
            hdrs.AUTHORIZATION: f"Bearer {credentials.token}",
            hdrs.ACCEPT: "application/json",
        }

        url = urljoin(self._config.portal_url, "api/" + PATH_API_IOT_CONTROL)
        # Ecovacs is setting not the correct content type in the response
        # even if the response is json
        return await _post(
            self._config.session,
            url,
            body,
            query_params=query_params,
            headers=headers,
            expected_content_type="application/octet-stream",
        )
