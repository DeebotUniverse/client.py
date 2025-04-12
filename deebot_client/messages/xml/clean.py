"""Clean messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import (
    CleanJobStatus,
    FanSpeedEvent,
    FanSpeedLevel,
    Position,
    PositionsEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage
from deebot_client.models import CleanAction, State
from deebot_client.rs.map import PositionType

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

        :return: A message response
        """
        return HandlingResult.analyse()


class CleanReport(XmlMessage):
    """CleanReport message."""

    NAME = "CleanReport"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl ts='1744467249311' td='CleanReport'><clean type='auto' speed='standard' st='s' rsn='a' a='' l='' sts=''/></ctl>"

        :return: A message response
        """
        if (clean := xml.find("clean")) is None:
            return HandlingResult.analyse()

        speed_attrib = clean.attrib.get("speed")
        if speed_attrib is not None:
            fan_speed_level = FanSpeedLevel.from_xml(speed_attrib)
            event_bus.notify(FanSpeedEvent(fan_speed_level))

        clean_attrib = clean.attrib.get("st")
        if clean_attrib is not None:
            clean_action = CleanAction.from_xml(clean_attrib)
            if clean_action == CleanAction.START:
                event_bus.notify(StateEvent(State.CLEANING))
            elif clean_action == CleanAction.PAUSE:
                event_bus.notify(StateEvent(State.PAUSED))
            else:
                _LOGGER.debug("Ignored CleanState %s", clean_action)

        return HandlingResult.success()


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
        if act := xml.attrib.get("act"):
            clean_session = xml.attrib.get("cs")
            last = xml.attrib.get("last")
            area = xml.attrib.get("area")
            type = xml.attrib.get("type")
            clean_action = CleanAction.from_xml(act)
            if clean_action == CleanAction.STOP:
                event_bus.notify(StatsEvent(area=area, time=last, type=type))
                event_reported = True
            if clean_session:
                if clean_action == CleanAction.STOP:
                    job_status = CleanJobStatus.FINISHED
                elif clean_action == CleanAction.START:
                    job_status = CleanJobStatus.CLEANING
                elif clean_action == CleanAction.PAUSE:
                    job_status = CleanJobStatus.PAUSED
                else:
                    job_status = CleanJobStatus.NO_STATUS
                event_bus.notify(
                    ReportStatsEvent(
                        area=area,
                        time=last,
                        type=type,
                        cleaning_id=clean_session,
                        status=job_status,
                        content=[],
                    )
                )
                event_reported = True
        if event_reported:
            return HandlingResult.success()
        return HandlingResult.analyse()


class CleanedPos(XmlMessage):
    """CleanedPos message."""

    NAME = "CleanedPos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl ts='1744467393682' td='CleanedPos' t='p' p='-2450,-996' a='-88' csid='1134230540'/>"

        :return: A message response
        """
        if p := xml.attrib.get("p"):
            p_x, p_y = p.split(",", 2)
            p_a = xml.attrib.get("a", 0)
            position = Position(
                type=PositionType.DEEBOT, x=int(p_x), y=int(p_y), a=int(p_a)
            )
            event_bus.notify(PositionsEvent(positions=[position]))
            return HandlingResult.success()

        return HandlingResult.analyse()
