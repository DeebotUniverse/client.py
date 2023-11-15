"""Common xml based commands."""
from abc import ABC
from typing import Any

from defusedxml import ElementTree

from deebot_client.command import Command, CommandResult
from deebot_client.event_bus import EventBus
from deebot_client.events import AvailabilityEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBody

_LOGGER = get_logger(__name__)


class XmlCommand(Command):
    """Xml command."""

    @property
    @classmethod
    def has_sub_element(cls) -> bool:
        """Return True if command has inner element."""
        return False

    def _get_payload(self) -> str:
        element = ctl_element = ElementTree.Element("ctl")

        if len(self._args) > 0:
            if self.has_sub_element:
                element = ElementTree.SubElement(element, self.name.lower())

            if isinstance(self._args, dict):
                for key, value in self._args.items():
                    element.set(key, value)

        return ElementTree.tostring(ctl_element, "unicode")


class CommandWithMessageHandling(XmlCommand, MessageBody, ABC):
    """Command, which handle response by itself."""

    _is_available_check: bool = False

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            result = self.handle(event_bus, data)
            return CommandResult(result.state, result.args)

        if errno := response.get("errno", None):
            match errno:
                case 4200:
                    # bot offline
                    _LOGGER.info(
                        'Vacuum is offline. Could not execute command "%s"', self.name
                    )
                    event_bus.notify(AvailabilityEvent(False))
                    return CommandResult(HandlingState.FAILED)
                case 500:
                    if self._is_available_check:
                        _LOGGER.info(
                            'No response received for command "%s" during availability-check.',
                            self.name,
                        )
                    else:
                        _LOGGER.warning(
                            'No response received for command "%s". This can happen if the vacuum has network issues or does not support the command',
                            self.name,
                        )
                    return CommandResult(HandlingState.FAILED)

        _LOGGER.warning('Command "%s" was not successfully.', self.name)
        return CommandResult(HandlingState.ANALYSE)


class ExecuteCommand(CommandWithMessageHandling, ABC):
    """Command, which is executing something (ex. Charge)."""

    @classmethod
    def _handle_body(
        cls, event_bus: EventBus, body: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """

        # Success events from the XML api looks like <ctl ret='ok'/>
        if isinstance(body, str):
            element = ElementTree.fromstring(body)
            if element.attrib.get("ret") == "ok":
                return HandlingResult.success()

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.name, body)
        return HandlingResult(HandlingState.FAILED)
