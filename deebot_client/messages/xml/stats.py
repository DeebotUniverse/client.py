"""Stats messages."""
from deebot_client.event_bus import EventBus
from deebot_client.message import HandlingResult, MessageBodyDataDict


class ReportStats(MessageBodyDataDict):
    """Report stats message."""

    name = "GetReportStats"

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        raise NotImplementedError
