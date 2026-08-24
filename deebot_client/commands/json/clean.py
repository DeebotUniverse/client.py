"""Clean commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import GoatCleanModeEvent, StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import ApiDeviceInfo, CleanAction, CleanMode, State

from .common import ExecuteCommand, JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class Clean(ExecuteCommand):
    """Clean command."""

    NAME = "clean"

    def __init__(self, action: CleanAction) -> None:
        super().__init__(self._get_args(action))

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        """Execute command."""
        state = event_bus.get_last_event(StateEvent)
        if state and isinstance(self._args, dict):
            if (
                self._args["act"] == CleanAction.RESUME.value
                and state.state != State.PAUSED
            ):
                self._args = self._get_args(CleanAction.START)
            elif (
                self._args["act"] == CleanAction.START.value
                and state.state == State.PAUSED
            ):
                self._args = self._get_args(CleanAction.RESUME)

        return await super()._execute(authenticator, device_info, event_bus)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = {"act": action.value}
        if action == CleanAction.START:
            args["type"] = CleanMode.AUTO.value
        return args


class CleanArea(Clean):
    """Clean area command."""

    def __init__(
        self, mode: CleanMode, area: list[int | float], cleanings: int = 1
    ) -> None:
        self._additional_args = {
            "type": mode.value,
            "content": ",".join(str(i) for i in area),
            "count": cleanings,
        }
        super().__init__(CleanAction.START)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args.update(self._additional_args)
        return args


class CleanV2(Clean):
    """Clean V2 command."""

    NAME = "clean_V2"

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        content: dict[str, str] = {}
        args = {"act": action.value, "content": content}
        match action:
            case CleanAction.START:
                content["type"] = CleanMode.AUTO.value
            case CleanAction.STOP | CleanAction.PAUSE:
                content["type"] = ""
        return args


class CleanAreaV2(CleanV2):
    """Clean area command."""

    def __init__(
        self, mode: CleanMode, area: list[int | float], cleanings: int = 1
    ) -> None:
        value = ",".join(str(i) for i in area)
        if mode == CleanMode.FREE_CLEAN:
            value = f"{cleanings},{value}"
        self._additional_content = {
            "type": mode.value,
            "value": value,
        }
        super().__init__(CleanAction.START)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args["content"].update(self._additional_content)
        return args


class GoatClean(Clean):
    """GOAT mower clean command using the observed ``clean`` wire shape."""

    def __init__(self, action: CleanAction, mode: CleanMode | None = None) -> None:
        self._mode = mode
        super().__init__(action)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        return {
            "act": action.value,
            "content": {
                "type": (self._mode or CleanMode.AUTO).value,
            },
        }

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        action = CleanAction.START
        if isinstance(self._args, dict) and isinstance(
            raw_action := self._args.get("act"), str
        ):
            action = CleanAction(raw_action)
        if self._mode is None:
            observed = event_bus.get_last_event(GoatCleanModeEvent)
            observed_mode = (
                CleanMode(observed.mode)
                if isinstance(observed, GoatCleanModeEvent)
                and observed.mode
                in {CleanMode.AUTO.value, CleanMode.SPOT_AREA.value}
                else None
            )
            state = event_bus.get_last_event(StateEvent)
            if action == CleanAction.START:
                self._mode = (
                    observed_mode
                    if observed_mode is not None
                    and isinstance(state, StateEvent)
                    and state.state == State.PAUSED
                    else CleanMode.AUTO
                )
            else:
                self._mode = observed_mode or CleanMode.AUTO
        self._args = self._get_args(action)
        event_bus.notify(GoatCleanModeEvent((self._mode or CleanMode.AUTO).value))
        return await super()._execute(authenticator, device_info, event_bus)


class GoatCleanArea(GoatClean):
    """Start one or more GOAT work areas using observed comma serialization."""

    def __init__(
        self, mode: CleanMode, area: list[int | float], cleanings: int = 1
    ) -> None:
        if mode != CleanMode.SPOT_AREA:
            raise ValueError("GOAT area cleaning requires spotArea mode")
        if cleanings != 1:
            raise ValueError("GOAT area cleaning supports exactly one cleaning")
        if not area or any(
            not isinstance(area_id, int) or isinstance(area_id, bool)
            for area_id in area
        ):
            raise ValueError("GOAT area cleaning requires integer area IDs")
        self._area_ids = area
        super().__init__(CleanAction.START, mode=CleanMode.SPOT_AREA)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args["content"]["value"] = ",".join(
                str(area_id) for area_id in self._area_ids
            )
        return args


class GetCleanInfo(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get clean info command."""

    NAME = "getCleanInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status: State | None = None
        state = data.get("state")
        if data.get("trigger") == "alert":
            status = State.ERROR
        elif state in ("clean", "washing"):
            clean_state = data.get("cleanState", {})
            motion_state = clean_state.get("motionState")
            if motion_state == "working":
                status = State.CLEANING
            elif motion_state == "pause":
                status = State.PAUSED
            elif motion_state == "goCharging":
                status = State.RETURNING

            clean_type = clean_state.get("type")
            content = clean_state.get("content", {})
            if "type" in content:
                clean_type = content.get("type")

            if (
                getattr(event_bus.capabilities, "device_type", None) == "mower"
                and clean_type in {CleanMode.AUTO.value, CleanMode.SPOT_AREA.value}
            ):
                event_bus.notify(GoatCleanModeEvent(clean_type))

            if clean_type == "customArea":
                area_values = content
                if "value" in content:
                    area_values = content.get("value")

                _LOGGER.debug("Last custom area values (x1,y1,x2,y2): %s", area_values)

        elif state == "goCharging":
            status = State.RETURNING
        elif state == "idle":
            status = State.IDLE

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()


class GetCleanInfoV2(GetCleanInfo):
    """Get clean info v2 command."""

    NAME = "getCleanInfo_V2"
