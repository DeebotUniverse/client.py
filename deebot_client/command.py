"""Base command."""
from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from typing import Any, final

from deebot_client.exceptions import DeebotError

from .authentication import Authenticator
from .const import PATH_API_IOT_DEVMANAGER, REQUEST_HEADERS, DataType
from .event_bus import EventBus
from .logging_filter import get_logger
from .message import HandlingResult, HandlingState
from .models import DeviceInfo

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class CommandResult(HandlingResult):
    """Command result object."""

    requested_commands: list["Command"] = field(default_factory=list)

    @classmethod
    def success(cls) -> "CommandResult":
        """Create result with handling success."""
        return CommandResult(HandlingState.SUCCESS)

    @classmethod
    def analyse(cls) -> "CommandResult":
        """Create result with handling analyse."""
        return CommandResult(HandlingState.ANALYSE)


class Command(ABC):
    """Abstract command object."""

    _targets_bot: bool = True

    def __init__(self, args: dict[str, Any] | list[Any] | None = None) -> None:
        if args is None:
            args = {}
        self._args = args

    @property  # type: ignore[misc]
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Command name."""

    @property  # type: ignore[misc]
    @classmethod
    @abstractmethod
    def data_type(cls) -> DataType:
        """Data type."""  # noqa: D401

    @abstractmethod
    def _get_payload(self) -> dict[str, Any] | list[Any] | str:
        """Get the payload for the rest call."""

    @final
    async def execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> bool:
        """Execute command.

        Returns
        -------
            bot_reached (bool): True if the command was targeting the bot and it responded in time. False otherwise.
                                This value is not indicating if the command was executed successfully.
        """
        try:
            result = await self._execute(authenticator, device_info, event_bus)
            if result.state == HandlingState.SUCCESS:
                # Execute command which are requested by the handler
                async with asyncio.TaskGroup() as tg:
                    for requested_command in result.requested_commands:
                        tg.create_task(
                            requested_command.execute(
                                authenticator, device_info, event_bus
                            )
                        )

                return self._targets_bot
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Could not execute command %s",
                self.name,
                exc_info=True,
            )
        return False

    async def _execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        """Execute command."""
        response = await self._execute_api_request(authenticator, device_info)

        result = self.__handle_response(event_bus, response)
        if result.state == HandlingState.ANALYSE:
            _LOGGER.debug(
                "ANALYSE: Could not handle command: %s with %s", self.name, response
            )
            return CommandResult(
                HandlingState.ANALYSE_LOGGED,
                result.args,
                result.requested_commands,
            )
        if result.state == HandlingState.ERROR:
            _LOGGER.warning("Could not parse %s: %s", self.name, response)
        return result

    async def _execute_api_request(
        self, authenticator: Authenticator, device_info: DeviceInfo
    ) -> dict[str, Any]:
        payload = {
            "cmdName": self.name,
            "payload": self._get_payload(),
            "payloadType": self.data_type.value,
            "td": "q",
            "toId": device_info.did,
            "toRes": device_info.resource,
            "toType": device_info.get_class,
        }

        credentials = await authenticator.authenticate()
        query_params = {
            "mid": payload["toType"],
            "did": payload["toId"],
            "td": payload["td"],
            "u": credentials.user_id,
            "cv": "1.67.3",
            "t": "a",
            "av": "1.3.1",
        }

        return await authenticator.post_authenticated(
            PATH_API_IOT_DEVMANAGER,
            payload,
            query_params=query_params,
            headers=REQUEST_HEADERS,
        )

    def __handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        try:
            result = self._handle_response(event_bus, response)
            if result.state == HandlingState.ANALYSE:
                _LOGGER.debug(
                    "ANALYSE: Could not handle command: %s with %s", self.name, response
                )
                return CommandResult(
                    HandlingState.ANALYSE_LOGGED,
                    result.args,
                    result.requested_commands,
                )
            return result
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Could not parse response for %s: %s",
                self.name,
                response,
                exc_info=True,
            )
            return CommandResult(HandlingState.ERROR)

    @abstractmethod
    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """

    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Command):
            return self.name == obj.name and self._args == obj._args

        return False

    def __hash__(self) -> int:
        return hash(self.name) + hash(self._args)


@dataclass
class InitParam:
    """Init param."""

    type_: type
    name: str | None = None


class CommandMqttP2P(Command, ABC):
    """Command which can handle mqtt p2p messages."""

    _mqtt_params: dict[str, InitParam | None]

    @abstractmethod
    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""

    @classmethod
    def create_from_mqtt(cls, data: dict[str, Any]) -> "CommandMqttP2P":
        """Create a command from the mqtt data."""
        values: dict[str, Any] = {}
        if not hasattr(cls, "_mqtt_params"):
            raise DeebotError("_mqtt_params not set")

        for name, param in cls._mqtt_params.items():
            if param is None:
                # Remove field
                data.pop(name, None)
            else:
                values[param.name or name] = _pop_or_raise(name, param.type_, data)

        if data:
            _LOGGER.debug("Following data will be ignored: %s", data)

        return cls(**values)


def _pop_or_raise(name: str, type_: type, data: dict[str, Any]) -> Any:
    try:
        value = data.pop(name)
    except KeyError as err:
        raise DeebotError(f'"{name}" is missing in {data}') from err
    try:
        return type_(value)
    except ValueError as err:
        raise DeebotError(
            f'Could not convert "{value}" of {name} into {type_}'
        ) from err
