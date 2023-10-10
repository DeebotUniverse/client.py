from deebot_client.authentication import Authenticator
from deebot_client.command import CommandResult
from deebot_client.commands.json.clean import CleanAction, CleanMode
from deebot_client.commands.json.common import ExecuteCommand, NoArgsCommand
from deebot_client.events import StateEvent
from deebot_client.events.event_bus import EventBus
from deebot_client.message import HandlingResult, MessageBodyDataDict

from xml.etree import ElementTree

from deebot_client.models import DeviceInfo, VacuumState

@unique
class CleanSpeed(str, Enum):
    """Enum class for all possible clean speeds.

    Currently only used for the Deebot 900.
    """

    STANDARD = "standard"
    STRONG = "strong"

class GetCleanInfo(NoArgsCommand, MessageBodyDataDict):
    """Get clean info command."""

    name = "GetCleanState"

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        
        status: VacuumState | None = None

        tree = ElementTree.fromstring(xml_message)

        element = tree.find("clean")
        if element is None:
            return HandlingResult.analyse()

        raw_state = element.attrib.get("st")
        a = element.attrib.get("a")  # Action ?

        if raw_state == "h" and a == "0":
            status = VacuumState.IDLE
        elif raw_state == "p" and a == "0":
            status = VacuumState.PAUSED
        elif raw_state == "s" and a == "0":
            status = VacuumState.CLEANING
        elif raw_state == "h" and a == "1":
            status = VacuumState.RETURNING

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()

class CleanArea(Clean):
    """Clean area command."""

    def __init__(self, mode: CleanMode, area: str, cleanings: int = 1) -> None:
        super().__init__(CleanAction.START)
        if not isinstance(self._args, dict):
            raise ValueError("args must be a dict!")

        self._args["type"] = mode.value
        self._args["content"] = str(area)
        self._args["count"] = cleanings

class Clean(ExecuteCommand):

    name = "Clean"

    has_sub_element = True

    async def _execute(self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus) -> CommandResult:
        state = event_bus.get_last_event(StateEvent)

        if state and isinstance(self._args, dict):
            if (
                self._args["act"] == CleanAction.RESUME.value
                and state.state != VacuumState.PAUSED
            ):
                self._args = str(self.__get_args(CleanAction.START))[0]
            elif (
                self._args["act"] == CleanAction.START.value
                and state.state == VacuumState.PAUSED
            ):
                self._args = str(self.__get_args(CleanAction.RESUME))[0]
            elif self._args["act"] == CleanAction.START.value:
                self._args["act"] = str(CleanAction.START.value)[0]

            elif self._args["act"] == CleanAction.STOP.value:
                self._args["act"] = str(CleanAction.HALT.value)[0]

            if "speed" not in self._args:
                self._args["speed"] = CleanSpeed.STANDARD.value

        return await super()._execute(authenticator, device_info, event_bus)