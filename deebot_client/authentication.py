"""Authentication module."""
import asyncio
import time
from collections.abc import Callable, Coroutine, Mapping
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, hdrs

from .const import REALM
from .exceptions import ApiError, AuthenticationError, InvalidAuthenticationError
from .logging_filter import get_logger
from .models import Configuration, Credentials
from .util import cancel, create_task, md5

_LOGGER = get_logger(__name__)

_CLIENT_KEY = "1520391301804"
_CLIENT_SECRET = "6c319b2a5cd3e66e39159c2e28f2fce9"
_AUTH_CLIENT_KEY = "1520391491841"
_AUTH_CLIENT_SECRET = "77ef58ce3afbe337da74aa8c5ab963a9"
_USER_LOGIN_URL_FORMAT = (
    "https://gl-{country}-api.ecovacs.{tld}/v1/private/{country}/{lang}/{deviceId}/{appCode}/"
    "{appVersion}/{channel}/{deviceType}/user/login"
)
_GLOBAL_AUTHCODE_URL_FORMAT = (
    "https://gl-{country}-openapi.ecovacs.{tld}/v1/global/auth/getAuthCode"
)
_PATH_USERS_USER = "users/user.do"
_META = {
    "lang": "EN",
    "appCode": "global_e",
    "appVersion": "1.6.3",
    "channel": "google_play",
    "deviceType": "1",
}
MAX_RETRIES = 3


def _get_portal_url(config: Configuration, path: str) -> str:
    subdomain = f"portal-{config.continent}" if config.country != "cn" else "portal"
    return urljoin(f"https://{subdomain}.ecouser.net/api/", path)


class _AuthClient:
    """Ecovacs auth client."""

    def __init__(
        self,
        config: Configuration,
        account_id: str,
        password_hash: str,
    ):
        self._config = config
        self._account_id = account_id
        self._password_hash = password_hash
        self._tld = "com" if self._config.country != "cn" else "cn"

        self._meta: dict[str, str] = {
            **_META,
            "country": self._config.country,
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
            url, params=params, timeout=60, ssl=self._config.verify_ssl
        ) as res:
            res.raise_for_status()

            # ecovacs returns a json but content_type header is set to text
            content_type = res.headers.get(hdrs.CONTENT_TYPE, "").lower()
            json = await res.json(content_type=content_type)
            _LOGGER.debug("got %s", json)
            # todo better error handling # pylint: disable=fixme
            if json["code"] == "0000":
                data: dict[str, Any] = json["data"]
                return data
            if json["code"] in ["1005", "1010"]:
                raise InvalidAuthenticationError

            _LOGGER.error("call to %s failed with %s", url, json)
            raise AuthenticationError(
                f"failure code {json['code']} ({json['msg']}) for call {url}"
            )

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

        url = _USER_LOGIN_URL_FORMAT.format(**self._meta, tld=self._tld)

        if self._config.country.lower() == "cn":
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

        url = _GLOBAL_AUTHCODE_URL_FORMAT.format(**self._meta, tld=self._tld)

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
            "org": "ECOWW" if self._config.country != "cn" else "ECOCN",
            "last": "",
            "country": self._config.country.upper()
            if self._config.country != "cn"
            else "Chinese",
            "todo": "loginByItToken",
        }

        for i in range(3):
            resp = await self.post(_PATH_USERS_USER, data)
            if resp["result"] == "ok":
                return resp
            if resp["result"] == "fail" and resp["error"] == "set token error.":
                # If it is a set token error try again
                _LOGGER.warning("loginByItToken set token error, attempt %d/3", i + 2)
                continue

            _LOGGER.error("call to %s failed with %s", _PATH_USERS_USER, resp)
            raise AuthenticationError(
                f"failure {resp['error']} ({resp['errno']}) for call {_PATH_USERS_USER}"
            )

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
        url = _get_portal_url(self._config, path)
        logger_requst_params = f"url={url}, params={query_params}, json={json}"

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
                logger_requst_params,
            )

            try:
                async with self._config.session.post(
                    url,
                    json=json,
                    params=query_params,
                    headers=headers,
                    timeout=60,
                    ssl=self._config.verify_ssl,
                ) as res:
                    if res.status == 200:
                        response_data: dict[str, Any] = await res.json()
                        _LOGGER.debug(
                            "Success calling api %s, response=%s",
                            logger_requst_params,
                            response_data,
                        )
                        return response_data

                    _LOGGER.debug(
                        "Error calling api %s, response=%s", logger_requst_params, res
                    )
                    raise ClientResponseError(
                        res.request_info,
                        res.history,
                        status=res.status,
                        message=str(res.reason),
                        headers=res.headers,
                    )
            except asyncio.TimeoutError as ex:
                _LOGGER.warning(
                    "Timeout reached on api path: %s%s", path, json.get("cmdName", "")
                )
                raise ApiError("Timeout reached") from ex
            except ClientResponseError as ex:
                _LOGGER.debug("Error: %s", logger_requst_params, exc_info=True)
                if ex.status == 502:
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
        config: Configuration,
        account_id: str,
        password_hash: str,
    ):
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

    async def authenticate(self, force: bool = False) -> Credentials:
        """Authenticate on ecovacs servers."""
        async with self._lock:
            should_login = False
            if self._credentials is None or force:
                _LOGGER.debug("No cached credentials, performing login")
                should_login = True
            elif self._credentials.expires_at < time.time():
                _LOGGER.debug("Credentials have expired, performing login")
                should_login = True

            if should_login:
                self._credentials = await self._auth_client.login()
                self._cancel_refresh_task()
                self._create_refresh_task()

                for on_changed in self._on_credentials_changed:
                    create_task(self._tasks, on_changed(self._credentials))

            assert self._credentials is not None
            return self._credentials

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

    def _create_refresh_task(self) -> None:
        # refresh at 99% of validity
        def refresh() -> None:
            _LOGGER.debug("Refresh token")

            async def async_refresh() -> None:
                try:
                    await self.authenticate(True)
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "An exception occurred during refreshing token", exc_info=True
                    )

            create_task(self._tasks, async_refresh())
            self._refresh_handle = None

        assert self._credentials is not None
        validity = (self._credentials.expires_at - time.time()) * 0.99

        self._refresh_handle = asyncio.get_event_loop().call_later(validity, refresh)
