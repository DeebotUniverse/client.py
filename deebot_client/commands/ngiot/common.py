"""Common NGIOT command helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from deebot_client.commands.json.common import ExecuteCommand, JsonGetCommand
from deebot_client.exceptions import ApiError
from deebot_client.ngiot_client import NgiotRequest

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.models import ApiDeviceInfo, DeviceInfo
    from deebot_client.ngiot_client import NgiotClient


APN_ROBOT_DETAIL = "10001"
APN_CLEAN_START = "40001"
APN_AREA_CLEAN = "40007"
APN_PAUSE = "40009"
APN_RESUME = "40011"
APN_RETURN_TO_DOCK = "40013"
APN_DEVICE_LOCATE = "40019"
APN_FAN_MODE = "50011"
APN_RESET_CONSUMABLE = "50017"
APN_SET_VOLUME = "50023"
APN_CHILD_LOCK = "50038"


class NgiotCommandMixin(ABC):
    """Mixin that routes command execution through ``Authenticator.ngiot_client``."""

    async def _get_ngiot_client(
        self,
        authenticator: Authenticator,
        _: ApiDeviceInfo | DeviceInfo,
    ) -> NgiotClient:
        client = getattr(authenticator, "ngiot_client", None)
        if client is None:
            msg = "NGIOT client is not attached to authenticator"
            raise ApiError(msg)
        return cast("NgiotClient", client)

    @staticmethod
    def _wrap_response(response: Mapping[str, Any]) -> dict[str, Any]:
        """Wrap a raw NGIOT envelope in the existing command response shape."""
        body = response.get("body", {})
        if not isinstance(body, Mapping):
            body = {}
        return {"ret": "ok", "resp": {"body": dict(body)}}

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        client = await self._get_ngiot_client(authenticator, device_info)
        response = await self._request_ngiot(client, device_info)
        return self._wrap_response(response)

    @abstractmethod
    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """Execute the NGIOT request and return the raw NGIOT envelope."""


class NgiotGetCommand(NgiotCommandMixin, JsonGetCommand, ABC):
    """Base class for NGIOT-backed get commands."""

    def __init__(
        self,
        args: dict[str, Any] | list[Any] | None = None,
        *,
        is_available_check: bool = False,
    ) -> None:
        super().__init__(args)
        self._is_available_check = is_available_check


class NgiotExecuteCommand(NgiotCommandMixin, ExecuteCommand, ABC):
    """Base class for NGIOT-backed execute commands."""


class NgiotRequestCommand(NgiotCommandMixin, ExecuteCommand, ABC):
    """Base class for commands backed by an explicit NGIOT request."""

    def __init__(self, request: NgiotRequest) -> None:
        args = dict(request.body_data) if isinstance(request.body_data, Mapping) else {}
        super().__init__(args)
        self._request = request

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(device_info, self._request)


class RobotDetailGetCommand(NgiotGetCommand, ABC):
    """Base class for APN 10001 field queries."""

    FIELDS: tuple[str, ...] = ()

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(
            device_info,
            NgiotRequest(
                apn=APN_ROBOT_DETAIL,
                body_data={"fields": list(self.FIELDS)},
            ),
        )


class NgiotWriteCommand(NgiotExecuteCommand, ABC):
    """Base class for direct key/value NGIOT write commands."""

    APN: str

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        return await client.request(
            device_info,
            NgiotRequest(apn=self.APN, body_data=self._get_body_data()),
        )

    @abstractmethod
    def _get_body_data(self) -> dict[str, Any] | Sequence[Any]:
        """Return the NGIOT request body payload."""
