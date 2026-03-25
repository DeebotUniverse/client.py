"""Common NGIOT command helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
import inspect

from deebot_client.commands.json.common import ExecuteCommand, JsonGetCommand
from deebot_client.exceptions import ApiError
from deebot_client.ngiot_client import APN_ROBOT_DETAIL

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


class NgiotJsonCommandMixin(ABC):
    """Mixin that routes command execution through ``Authenticator.ngiot_client``.

    The upstream command stack expects responses in the legacy devmanager shape,
    i.e. ``{"ret": "ok", "resp": {"body": ...}}``. NGIOT returns a raw
    ``{"header": ..., "body": ...}`` envelope, so this mixin adapts the raw
    response into the shape already handled by ``CommandWithMessageHandling``.
    """

    async def _execute_api_request(  # type: ignore[override]
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        client = await self._get_ngiot_client(authenticator, device_info)
        response = await self._request_ngiot(client, device_info)
        return self._wrap_response(response)

    async def _get_ngiot_client(self, authenticator, device_info):
        client = getattr(authenticator, "ngiot_client", None)
        if client is not None:
            return client

        ensure = getattr(authenticator, "ensure_ngiot_for_device", None)
        if ensure is not None:
            raw_device = device_info.api if hasattr(device_info, "api") else device_info
            result = ensure(raw_device)
            if inspect.isawaitable(result):
                await result

            client = getattr(authenticator, "ngiot_client", None)
            if client is not None:
                return client

        raise ApiError(
            "NGIOT client not attached to authenticator after bootstrap attempt"
        )

    @staticmethod
    def _wrap_response(response: Mapping[str, Any]) -> dict[str, Any]:
        body = response.get('body', {})
        if not isinstance(body, Mapping):
            body = {}
        return {'ret': 'ok', 'resp': {'body': dict(body)}}

    @abstractmethod
    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """Execute the NGIOT request and return the raw NGIOT envelope."""


class NgiotJsonGetCommand(NgiotJsonCommandMixin, JsonGetCommand, ABC):
    """Base class for NGIOT-backed get commands."""

    def __init__(
        self,
        args: dict[str, Any] | list[Any] | None = None,
        *,
        is_available_check: bool = False,
    ) -> None:
        super().__init__(args)
        self._is_available_check = is_available_check


class NgiotExecuteCommand(NgiotJsonCommandMixin, ExecuteCommand, ABC):
    """Base class for NGIOT-backed execute commands."""


class RobotDetailGetCommand(NgiotJsonGetCommand, ABC):
    """Base class for APN 10001 field queries."""

    FIELDS: tuple[str, ...] = ()

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(
            device_info,
            apn=APN_ROBOT_DETAIL,
            body_data={'fields': list(self.FIELDS)},
        )


class RobotDetailSetCommand(NgiotExecuteCommand, ABC):
    """Base class for APN 10001 writes."""

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(
            device_info,
            apn=APN_ROBOT_DETAIL,
            body_data=self._get_body_data(),
        )

    @abstractmethod
    def _get_body_data(self) -> dict[str, Any] | list[Any]:
        """Return the NGIOT request body payload."""
