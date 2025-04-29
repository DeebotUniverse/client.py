"""Map commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.command import Command, CommandResult
from deebot_client.events import MajorMapEvent, MapSetEvent, MapSetType, MinorMapEvent
from deebot_client.events.map import CachedMapInfoEvent, MapSubsetEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from typing import Any
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetMapSt(XmlCommandWithMessageHandling):
    """GetMapSt command.

    This command checks whether the current map has been built successfully or not.
    """

    NAME = "GetMapSt"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        Sample message response:
        "<ctl ret='ok' st='built' method='auto'/>"

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (st := xml.attrib.get("st")):
            return HandlingResult.analyse()

        built = st == "built"
        event_bus.notify(CachedMapInfoEvent(name="", active=built))
        return HandlingResult.success()

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            return CommandResult(
                result.state,
                result.args,
                [GetMapSet(entry) for entry in MapSetType],
            )

        return result


class GetMapSet(XmlCommandWithMessageHandling):
    """GetMapSet command.

    This commands gets the list of logical pieces each map is composed of.
    XML robots do not support multiple maps, so the mid parameter is ignored.
    """

    _ARGS_MSID = "msid"
    _ARGS_TYPE = "type"
    _ARGS_SUBSETS = "subsets"

    NAME = "GetMapSet"

    def __init__(
        self,
        map_set_type: (MapSetType | str) = MapSetType.VIRTUAL_WALLS,
    ) -> None:
        if isinstance(map_set_type, MapSetType):
            map_set_type = map_set_type.value

        super().__init__({"tp": map_set_type})

    @classmethod
    def _find_subsets(cls, maps: list[Element]) -> list[int]:
        return [int(mid) for map in maps if (mid := map.attrib.get("mid")) is not None]

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        Sample message response:
        b'<ctl ret="ok" tp="vw" msid="1"><m mid="1" p="1" /><m mid="2" p="1" /></ctl>'

        :return: A message response
        """
        if (
            xml.attrib.get("ret") != "ok"
            or not (msid := xml.attrib.get("msid"))
            or not (area_type := xml.attrib.get("tp"))
            or not MapSetType.has_value(area_type)
        ):
            return HandlingResult.analyse()

        xml_subsets = xml.findall("m")
        subsets = cls._find_subsets(xml_subsets)
        event_bus.notify(MapSetEvent(MapSetType(area_type), subsets=subsets))
        args = {
            cls._ARGS_MSID: msid,
            cls._ARGS_TYPE: area_type,
            cls._ARGS_SUBSETS: subsets,
        }
        return HandlingResult(HandlingState.SUCCESS, args)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            commands: list[Command] = [
                PullM(
                    mid=subset,
                    msid=result.args[self._ARGS_MSID],
                    type=result.args[self._ARGS_TYPE],
                )
                for subset in result.args[self._ARGS_SUBSETS]
            ]
            return CommandResult(result.state, result.args, commands)

        return result


class GetMapM(XmlCommandWithMessageHandling):
    """GetMapM command."""

    NAME = "GetMapM"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        Sample message response:
        b'<ctl i="1245233875" w="100" h="100" r="8" c="8" p="50" m="1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1233223751,1788503751,4083617034,1295764014,1295764014,1295764014,1295764014,1295764014,315201502,2976702022,2972256573,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014" />'

        :return: A message response
        """
        if not (map_hashes := xml.attrib.get("m")) or not (idx := xml.attrib.get("i")):
            return HandlingResult.analyse()
        event_bus.notify(
            MajorMapEvent(
                idx,
                values=[int(map_hash.strip()) for map_hash in map_hashes.split(",")],
                requested=True,
            )
        )
        return HandlingResult.success()


class PullM(XmlCommandWithMessageHandling):
    """PullM command.

    Pulls map subset coordinates
    """

    _ARG_COORDS = "coordinates"

    NAME = "PullM"

    def __init__(
        self,
        *,
        mid: str | int,
        msid: str | int,
        # pylint: disable=redefined-builtin
        type: (MapSetType | str) = MapSetType.ROOMS,
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value

        self._map_type = type
        self._map_subset_id = int(mid)

        super().__init__(
            {
                "mid": str(mid),
                "msid": str(msid),
                "tp": type,
                "seq": "0",
            },
        )

    @classmethod
    def _handle_xml(cls, _event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        Sample message responses:
        <ctl ret='ok' m='[751,-960,751,-1242,1118,-1242,1118,-960]'/>
        <ctl ret='ok' m='-3000,-4400;-3000,-3650;-2450,-3500;-2450,-2400;-2350,-2300;-2350,-1500;-1750,-1500;-1650,-1600;-1250,-1550;-1250,-2300;-1350,-2300;-1600,-2550;-1500,-2750;-1500,-3850;-1750,-3850;-2100,-4200;-2100,-4450;-2150,-4400;-3000,-4400'/>

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (coords := xml.attrib.get("m")):
            return HandlingResult.analyse()

        args = {cls._ARG_COORDS: coords}
        return HandlingResult(HandlingState.SUCCESS, args)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            coords = result.args[self._ARG_COORDS]
            event_bus.notify(
                MapSubsetEvent(
                    id=self._map_subset_id,
                    type=MapSetType(self._map_type),
                    coordinates=coords,
                )
            )
            return CommandResult(result.state, result.args)

        return result


class PullMP(XmlCommandWithMessageHandling):
    """PullMP command."""

    _ARG_PIECE = "piece"

    NAME = "PullMP"

    def __init__(self, piece_index: int, _: str | None = None) -> None:
        self._piece_index = piece_index
        super().__init__({"pid": str(piece_index)})

    @classmethod
    def _handle_xml(cls, _: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        Sample message response:
        b{'ret': 'ok', 'i': '1839263381', 'p': 'x_q_a_a_b_a_a_q_jw_a_a_a_a_bv/f//o7f/_rz5_i_f_x_i5_y_v_g4kijmo4_y_h+e7k_ho_l_t_l8_u6_p_a_f_ls_x7_jhrz0_kg_a=', 'event': 'pull_m_p'}

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (piece := xml.attrib.get("p")):
            return HandlingResult.analyse()
        args = {cls._ARG_PIECE: piece}
        return HandlingResult(HandlingState.SUCCESS, args)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            piece = result.args[self._ARG_PIECE]
            event_bus.notify(MinorMapEvent(index=self._piece_index, value=piece))
            return CommandResult(result.state, result.args)

        return result


class GetTrM(XmlCommandWithMessageHandling):
    """GetTrM command.

    Enables trace reporting from the bot.
    """

    NAME = "GetTrM"

    @classmethod
    def _handle_xml(cls, _: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()
        return HandlingResult(HandlingState.SUCCESS)
