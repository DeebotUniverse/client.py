"""Base command."""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, final

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

    requested_commands: list["Command"] | None = None

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

    def __init__(self, args: dict | list | None = None) -> None:
        if args is None:
            args = {}
        self._args = args

    @property  # type: ignore[misc]
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Command name."""

    @final
    async def execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> None:
        """Execute command."""
        try:
            result = await self._execute(authenticator, device_info, event_bus)
            if result.state == HandlingState.SUCCESS and result.requested_commands:
                # Execute command which are requested by the handler
                tasks = []
                for requested_command in result.requested_commands:
                    tasks.append(
                        asyncio.create_task(
                            requested_command.execute(
                                authenticator, device_info, event_bus
                            )
                        )
                    )

                await asyncio.gather(*tasks)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Could not execute command %s",
                self.name,
                exc_info=True,
            )

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

    async def _execute_api_request(
        self, authenticator: Authenticator, device_info: DeviceInfo
    ) -> dict[str, Any]:
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

        json = {
            "cmdName": self.name,
            "payload": payload,
            "payloadType": "j",
            "td": "q",
            "toId": device_info.did,
            "toRes": device_info.resource,
            "toType": device_info.get_class,
        }

        credentials = await authenticator.authenticate()
        query_params = {
            "mid": json["toType"],
            "did": json["toId"],
            "td": json["td"],
            "u": credentials.user_id,
            "cv": "1.67.3",
            "t": "a",
            "av": "1.3.1",
        }

        return await authenticator.post_authenticated(
            PATH_API_IOT_DEVMANAGER,
            json,
            query_params=query_params,
            headers=REQUEST_HEADERS,
        )

    def __handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        try:
            result = self._handle_requested(event_bus, response)
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
    def _handle_requested(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """

    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Command):
            return self.name == obj.name and self._args == obj._args

        return False

    def __hash__(self) -> int:
        return hash(self.name) + hash(self._args)
