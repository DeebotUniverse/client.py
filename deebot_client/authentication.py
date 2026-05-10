"""Authentication module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs

from .const import (
    AUTH_DOMAIN_ECOVACS,
    AUTH_DOMAIN_YEEDI,
    COUNTRY_CHINA,
    PATH_API_USERS_USER,
    REALM,
)
from .exceptions import (
    ApiError,
    ApiTimeoutError,
    AuthenticationError,
    InvalidAuthenticationError,
)
from .logging_filter import get_logger
from .models import Credentials
from .util import cancel, create_task, md5
from .util.continents import get_continent_url_postfix
from .util.countries import get_ecovacs_country

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Mapping


_LOGGER = get_logger(__name__)

_USER_LOGIN_PATH_FORMAT = "/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}/user/login"
_GLOBAL_AUTHCODE_PATH = "/v1/global/auth/getAuthCode"
_META = {
    "lang": "EN",
    "channel": "google_play",
    "deviceType": "1",
}
MAX_RETRIES = 3


@dataclass(frozen=True, kw_only=True)
class AuthDomainConfiguration:
    """Authentication configuration for an Ecovacs-family app domain."""

    domain: str
    app_code: str
    app_version: str
    user_login_auth_appkey: str
    user_login_secret: str
    get_auth_code_auth_appkey: str
    get_auth_code_secret: str
    get_auth_code_biz_type: str
    org_global: str
    org_china: str
    command_client_version: str
    command_app_version: str


_AUTH_CONFIGS = {
    AUTH_DOMAIN_ECOVACS: AuthDomainConfiguration(
        domain=AUTH_DOMAIN_ECOVACS,
        app_code="global_e",
        app_version="1.6.3",
        user_login_auth_appkey="1520391301804",
        user_login_secret="6c319b2a5cd3e66e39159c2e28f2fce9",  # noqa: S106
        get_auth_code_auth_appkey="1520391491841",
        get_auth_code_secret="77ef58ce3afbe337da74aa8c5ab963a9",  # noqa: S106
        get_auth_code_biz_type="ECOVACS_IOT",
        org_global="ECOWW",
        org_china="ECOCN",
        command_client_version="1.67.3",
        command_app_version="1.3.1",
    ),
    AUTH_DOMAIN_YEEDI: AuthDomainConfiguration(
        domain=AUTH_DOMAIN_YEEDI,
        app_code="yd_global_e",
        app_version="1.3.0",
        user_login_auth_appkey="1581917520081",
        user_login_secret="ed5b3dd9a0253de7d90305d077eb5fee",  # noqa: S106
        get_auth_code_auth_appkey="1581923437995",
        get_auth_code_secret="304a71592690995b2bb304e66b5ddee6",  # noqa: S106
        get_auth_code_biz_type="",
        org_global="ECOYDWW",
        org_china="ECOYDCN",
        command_client_version="1.94.76",
        command_app_version="1.3.0",
    ),
}


@dataclass(frozen=True, kw_only=True)
class RestConfiguration:
    """Rest configuration."""

    session: ClientSession
    device_id: str
    country: str
    portal_url: str
    login_url: str
    auth_code_url: str
    auth: AuthDomainConfiguration = _AUTH_CONFIGS[AUTH_DOMAIN_ECOVACS]


def create_rest_config(
    session: ClientSession,
    *,
    device_id: str,
    alpha_2_country: str,
    auth_domain: str = AUTH_DOMAIN_ECOVACS,
    override_rest_url: str | None = None,
) -> RestConfiguration:
    """Create configuration."""
    auth = _AUTH_CONFIGS.get(auth_domain.lower())
    if auth is None:
        msg = f"Unsupported auth domain: {auth_domain}"
        raise ValueError(msg)

    continent_postfix = get_continent_url_postfix(alpha_2_country)
    country = get_ecovacs_country(alpha_2_country)
    if override_rest_url:
        portal_url = login_url = auth_code_url = override_rest_url
    else:
        portal_url = f"https://portal{continent_postfix}.ecouser.net"
        country_url = country.lower()
        api_domain = auth.domain
        if country == COUNTRY_CHINA:
            api_domain = api_domain.removesuffix(".com") + ".cn"
        login_url = f"https://gl-{country_url}-api.{api_domain}"
        auth_code_url = f"https://gl-{country_url}-openapi.{api_domain}"

    return RestConfiguration(
        session=session,
        device_id=device_id,
        country=country,
        portal_url=portal_url,
        login_url=login_url,
        auth_code_url=auth_code_url,
        auth=auth,
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
            "appCode": self._config.auth.app_code,
            "appVersion": self._config.auth.app_version,
            "country": self._config.country.lower(),
            "deviceId": self._config.device_id,
        }

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
            url,
            self.__sign(
                params,
                self._meta,
                self._config.auth.user_login_auth_appkey,
                self._config.auth.user_login_secret,
            ),
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
            "bizType": self._config.auth.get_auth_code_biz_type,
            "deviceId": self._meta["deviceId"],
            "authTimespan": int(time.time() * 1000),
        }

        url = urljoin(self._config.auth_code_url, _GLOBAL_AUTHCODE_PATH)

        res = await self.__do_auth_response(
            url,
            self.__sign(
                params,
                {"openId": "global"},
                self._config.auth.get_auth_code_auth_appkey,
                self._config.auth.get_auth_code_secret,
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
            "org": self._config.auth.org_global
            if self._config.country != COUNTRY_CHINA
            else self._config.auth.org_china,
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

    def get_command_query_params(
        self, credentials: Credentials, *, mid: str, did: str, td: str
    ) -> dict[str, str]:
        """Return app metadata used for direct device command requests."""
        return {
            "mid": mid,
            "did": did,
            "td": td,
            "u": credentials.user_id,
            "cv": self._config.auth.command_client_version,
            "t": "a",
            "av": self._config.auth.command_app_version,
        }

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
            if (
                self._credentials is None
                or force
                or self._credentials.expires_at < time.time()
            ):
                _LOGGER.debug("Performing login")
                self._credentials = await self._auth_client.login()
                self._cancel_refresh_task()
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

    def get_command_query_params(
        self, credentials: Credentials, *, mid: str, did: str, td: str
    ) -> dict[str, str]:
        """Return app metadata used for direct device command requests."""
        return self._auth_client.get_command_query_params(
            credentials,
            mid=mid,
            did=did,
            td=td,
        )

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
