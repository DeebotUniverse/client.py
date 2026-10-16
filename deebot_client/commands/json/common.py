"""Base commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
import secrets
import time
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import aiohttp
import orjson

from deebot_client.command import (
    Command,
    CommandMqttP2P,
    CommandWithMessageHandling,
    GetCommand,
    InitParam,
    SetCommand,
)
from deebot_client.const import DataType
from deebot_client.logging_filter import get_logger
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageBody,
    MessageBodyDataDict,
)
from deebot_client.util import verify_required_class_variables_exists

from .const import CODE

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.events import EnableEvent

_LOGGER = get_logger(__name__)

_SST_URL = "https://api-base.dc-na.ww.ecouser.net/api/new-perm/token/sst/issue"
_NGIOT_URL = "https://api-ngiot.dc-na.ww.ecouser.net/api/iot/endpoint/control"

# Static signature block required by appsvr/app.do.
_APP_ID = "ecovacs"
_APP_SIGNATURE = "f66440b16af096f33575d1e396eab38e93991cc8"  # noqa: S105


async def get_sst(
    session: aiohttp.ClientSession,
    *,
    token: str,
    user_id: str,
    did: str,
    mid: str,
) -> str:
    """Obtain a Service Session Token (SST) for ngiot control commands."""
    body = {
        "acl": [
            {
                "policy": [{"obj": [f"Endpoint:{mid}:{did}"], "perms": ["Control"]}],
                "svc": "dim",
            }
        ],
        "exp": 600,
        "sub": user_id,
    }
    headers = {
        "authorization": f"Bearer {token}",
        "x-eco-request-id": secrets.token_hex(16),
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/4.9.1",
    }
    async with session.post(_SST_URL, json=body, headers=headers) as resp:
        data = await resp.json(content_type=None)
    return data["data"]["data"]["token"]  # type: ignore[no-any-return]


async def ngiot_post(
    session: aiohttp.ClientSession,
    *,
    sst: str,
    eid: str,
    et: str,
    er: str,
    apn: str,
    body_data: dict[str, Any],
) -> dict[str, Any]:
    """POST a command to the ngiot endpoint/control API."""
    si = secrets.token_urlsafe(12)[:16]
    reqid = secrets.token_urlsafe(6)[:6]
    params = {"si": si, "ct": "q", "eid": eid, "et": et, "er": er, "apn": apn, "fmt": "j"}
    payload: dict[str, Any] = {
        "body": {"data": body_data},
        "header": {
            "channel": "Android",
            "m": "request",
            "pri": 2,
            "reqid": reqid,
            "ts": str(int(time.time() * 1000)),
            "tzc": "Australia/Melbourne",
            "tzm": 600,
            "ver": "0.0.22",
        },
    }
    headers = {
        "authorization": f"Bearer {sst}",
        "appid": _APP_ID,
        "x-eco-request-id": reqid,
        "content-type": "application/json",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/4.9.1",
    }
    async with session.post(_NGIOT_URL, json=payload, params=params, headers=headers) as resp:
        text = await resp.text()
        return await resp.json(content_type=None) if text.strip() else {}  # type: ignore[no-any-return]


class JsonCommand(Command, ABC):
    """Json base command."""

    DATA_TYPE = DataType.JSON

    def _get_payload(self) -> dict[str, Any] | list[Any]:
        payload = {
            "header": {
                "pri": "1",
                "ts": time.time(),
                "tzm": 480,
                "ver": "0.0.50",
            }
        }

        if len(self._args) > 0:
            payload["body"] = {"data": self._args}

        return payload


class JsonCommandWithMessageHandling(
    JsonCommand, CommandWithMessageHandling, MessageBody, ABC
):
    """Command, which handle response by itself."""


class ExecuteCommand(JsonCommandWithMessageHandling, ABC):
    """Command, which is executing something (ex. Charge)."""

    @classmethod
    def _handle_body(cls, _: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        # Success event looks like { "code": 0, "msg": "ok" }
        if body.get(CODE, -1) == 0:
            return HandlingResult.success()

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.NAME, body)
        return HandlingResult(HandlingState.FAILED)


class JsonCommandMqttP2P(JsonCommand, CommandMqttP2P, ABC):
    """Json base command for mqtt p2p channel."""

    @classmethod
    def create_from_mqtt(cls, payload: str | bytes | bytearray) -> CommandMqttP2P:
        """Create a command from the mqtt data."""
        payload_json = orjson.loads(payload)
        data = payload_json["body"]["data"]
        return cls._create_from_mqtt(data)

    def handle_mqtt_p2p(
        self, event_bus: EventBus, response_payload: str | bytes | bytearray
    ) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        response = orjson.loads(response_payload)
        self._handle_mqtt_p2p(event_bus, response)

    @abstractmethod
    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""


class JsonSetCommand(ExecuteCommand, SetCommand, JsonCommandMqttP2P, ABC):
    """Json base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """


class JsonGetCommand(
    JsonCommandWithMessageHandling, MessageBodyDataDict, GetCommand, ABC
):
    """Json get command."""

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command."""
        return cls._handle_body_data_dict(event_bus, args)


class GetEnableCommand(JsonGetCommand, ABC):
    """Abstract get enable command."""

    _field_name: str = "enable"
    EVENT_TYPE: type[EnableEvent]

    def __init_subclass__(cls) -> None:
        verify_required_class_variables_exists(cls, ("EVENT_TYPE",))
        return super().__init_subclass__()

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event: EnableEvent = cls.EVENT_TYPE(bool(data[cls._field_name]))
        event_bus.notify(event)
        return HandlingResult.success()


_ENABLE = "enable"


class SetEnableCommand(JsonSetCommand, ABC):
    """Abstract set enable command."""

    _field_name = _ENABLE

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls._mqtt_params = MappingProxyType({cls._field_name: InitParam(bool, _ENABLE)})
        super().__init_subclass__(**kwargs)

    def __init__(self, enable: bool) -> None:
        super().__init__({self._field_name: 1 if enable else 0})
