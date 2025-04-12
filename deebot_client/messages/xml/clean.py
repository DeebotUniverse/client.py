"""Clean messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import (
    CleanJobStatus,
    FanSpeedEvent,
    FanSpeedLevel,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage
from deebot_client.messages.xml.pos import Pos
from deebot_client.models import CleanAction, State

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class CleanSt(XmlMessage):
    """CleanSt message."""

    NAME = "CleanSt"

    @classmethod
    def _handle_xml(cls, _event_bus: EventBus, _xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl td='CleanSt' a='21' s='1743945874' l='1595' t='' type='auto'/>"

        We currently ignore this message as we prefer to use CleanReport
        :return: A message response
        """
        return HandlingResult.success()


class CleanReport(XmlMessage):
    """CleanReport message."""

    NAME = "CleanReport"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl ts='1744467249311' td='CleanReport'><clean type='auto' speed='standard' st='s' rsn='a' a='' l='' sts=''/></ctl>"

        :return: A message response
        """
        return cls._parse_xml(event_bus, xml)

    @classmethod
    def _parse_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        if (clean := xml.find("clean")) is None:
            return HandlingResult.analyse()

        event_reported = False
        speed_attrib = clean.attrib.get("speed")
        if speed_attrib is not None:
            fan_speed_level = FanSpeedLevel.from_xml(speed_attrib)
            event_bus.notify(FanSpeedEvent(fan_speed_level))
            event_reported = True

        clean_attrib = clean.attrib.get("st")
        if clean_attrib is not None:
            clean_action = CleanAction.from_xml(clean_attrib)
            match clean_action:
                case CleanAction.START | CleanAction.RESUME:
                    event_bus.notify(StateEvent(State.CLEANING))
                    event_reported = True
                case CleanAction.PAUSE:
                    event_bus.notify(StateEvent(State.PAUSED))
                    event_reported = True
                case CleanAction.STOP:
                    event_bus.notify(StateEvent(State.IDLE))
                    event_reported = True

        if event_reported:
            return HandlingResult.success()
        return HandlingResult.analyse()


class CleanReportServer(XmlMessage):
    """CleanReportServer message."""

    NAME = "CleanReportServer"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl ts='1744467262312' td='CleanReportServer' act='s' type='auto' cs='1134230540'/>"
        b"<ctl ts='1744467393682' td='CleanReportServer' act='h' type='auto' sts='1744467262' cs='1134230540' area='1' last='76' mapCount='6'/>"

        :return: A message response
        """
        event_reported = False
        if (act := xml.attrib.get("act")) is not None:
            if (last := xml.attrib.get("last")) is not None and last.isdecimal():
                last_int = int(last)
            else:
                last_int = None

            if (area := xml.attrib.get("area")) is not None and area.isdecimal():
                area_int = int(area)
            else:
                area_int = None

            clean_session = xml.attrib.get("cs")
            clean_type = xml.attrib.get("type")

            clean_action = CleanAction.from_xml(act)
            if clean_action == CleanAction.STOP:
                event_bus.notify(
                    StatsEvent(area=area_int, time=last_int, type=clean_type)
                )
                event_reported = True
            if clean_session:
                job_status = CleanJobStatus.NO_STATUS
                match clean_action:
                    case CleanAction.STOP:
                        job_status = CleanJobStatus.FINISHED
                    case CleanAction.START | CleanAction.RESUME:
                        job_status = CleanJobStatus.CLEANING
                    case CleanAction.PAUSE:
                        job_status = CleanJobStatus.MANUALLY_STOPPED

                event_bus.notify(
                    ReportStatsEvent(
                        area=area_int,
                        time=last_int,
                        type=clean_type,
                        cleaning_id=clean_session,
                        status=job_status,
                        content=[],
                    )
                )
                event_reported = True

        if event_reported:
            return HandlingResult.success()
        return HandlingResult.analyse()


class CleanedPos(Pos):
    """CleanedPos message.

    We treat it as an alias of a standard Pos message.
    It is emitted while the bot is actively cleaning
    """

    NAME = "CleanedPos"
