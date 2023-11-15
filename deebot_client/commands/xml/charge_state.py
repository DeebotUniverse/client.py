"""Charge state commands."""
from xml.etree.ElementTree import Element
from deebot_client.commands.xml.common import XmlCommandWithMessageHandling
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State

_LOGGER = get_logger(__name__)


class GetChargeState(XmlCommandWithMessageHandling):
    """Get charge state comment"""

    name = 'GetChargeState'

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        # "<ctl ret='ok'><charge type='SlotCharging' g='1'/></ctl>" == docked and charging
        # "<ctl ret='ok'><charge type='Idle' g='0'/></ctl>"" == Idle (Potentially already fully charged?)

        element = xml.find('charge')

        if element is None:
            return HandlingResult(HandlingState.ERROR)

        xml_type = element.attrib.get("type")

        status: State | None = None
        if xml_type == "Idle":
            status = State.DOCKED
        elif xml_type == "SlotCharging":
            status = State.DOCKED

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()
