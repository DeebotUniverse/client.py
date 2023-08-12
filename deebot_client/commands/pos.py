"""Position command module."""

from typing import Any

from ..authentication import Authenticator
from ..command import CommandResult
from ..events import Position, PositionsEvent, PositionType
from ..message import HandlingResult, MessageBodyDataDict
from ..models import DeviceInfo
from .common import CommandWithMessageHandling, EventBus


class GetPos(CommandWithMessageHandling, MessageBodyDataDict):
    """Get volume command."""

    name = "getPos"

    xml_name = "GetPos"

    def __init__(self) -> None:
        super().__init__(["chargePos", "deebotPos"])

    async def _execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        if not device_info.uses_xml_protocol:
            return await super()._execute(authenticator, device_info, event_bus)

    @classmethod
    def _handle_body_data_xml(cls, event_bus: EventBus, xml_message: str):
        raise NotImplementedError

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        positions = []

        for type_str in ["deebotPos", "chargePos"]:
            data_positions = data.get(type_str, [])

            if isinstance(data_positions, dict):
                positions.append(
                    Position(
                        type=PositionType(type_str),
                        x=data_positions["x"],
                        y=data_positions["y"],
                    )
                )
            else:
                for entry in data_positions:
                    positions.append(
                        Position(
                            type=PositionType(type_str), x=entry["x"], y=entry["y"]
                        )
                    )

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()


class GetChargerPos(CommandWithMessageHandling, MessageBodyDataDict):
    """Get charger position command.

    This is currently only in use for the XML based devices,
    since they don't have a general "all positions" endpoint

    """

    name = "getChargerPos"

    xml_name = "GetChargerPos"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        raise NotImplementedError

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        pass
