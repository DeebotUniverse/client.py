"""Base command."""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, final
from xml.etree import ElementTree

from .authentication import Authenticator
from .const import PATH_API_IOT_DEVMANAGER, REQUEST_HEADERS
from .events.event_bus import EventBus
from .logging_filter import get_logger
from .message import HandlingResult, HandlingState
from .models import DeviceInfo

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class CommandResult(HandlingResult):
    """Command result object."""

    requested_commands: list["Command"] = field(default_factory=lambda: [])

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

    def __init__(self, args: dict | list | None = None) -> None:
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
    def xml_name(cls) -> str:
        """Command name."""

    @final
    async def execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> bool:
        """Execute command.

        Returns:
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
        return result

    def _get_json_payload(self) -> dict[str, Any] | list:
        payload = {
            "header": {
                "pri": "1",
                "ts": datetime.now().timestamp(),
                "tzm": 480,
                "ver": "0.0.50",
            }
        }

        if len(self._args) > 0:
            payload["body"] = {"data": self._args}

        return payload

    def _get_xml_payload(self) -> str:
        ctl_element = ElementTree.Element("ctl")

        if len(self._args) > 0:
            action_element = ElementTree.SubElement(ctl_element, self.xml_name.lower())

            for key in self._args:
                action_element.set(key, self._args[key])

        return ElementTree.tostring(ctl_element, "unicode")

        # return '<ctl/>'

    async def _execute_api_request(
        self, authenticator: Authenticator, device_info: DeviceInfo
    ) -> dict[str, Any]:
        if device_info.uses_xml_protocol:
            payload = self._generate_xml_payload(device_info)
        else:
            payload = self._generate_xml_payload(device_info)

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

    def _generate_json_payload(self, device_info: DeviceInfo):
        return {
            "cmdName": self.name,
            "payload": self._get_json_payload(),
            "payloadType": "j",
            "td": "q",
            "toId": device_info.did,
            "toRes": device_info.resource,
            "toType": device_info.get_class,
        }

    def _generate_xml_payload(self, device_info: DeviceInfo):
        return {
            "cmdName": self.xml_name,
            "payload": self._get_xml_payload(),
            "payloadType": "x",
            "td": "q",
            "toId": device_info.did,
            "toRes": device_info.resource,
            "toType": device_info.get_class,
        }

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
