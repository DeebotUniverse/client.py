"""Clean commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json.clean_info import OnCleanInfo
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


class CleanMower(Clean):
    """GOAT mower clean command.

    The Ecovacs Home app controls the GOAT O500 Panorama (``300lc5``) with
    ``clean``, not ``clean_V2``. ``content.type`` is included for start, pause,
    resume, and stop. A full-yard run uses ``auto``.
    """

    NAME = "clean"
    _mode: CleanMode = CleanMode.AUTO

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        state = event_bus.get_last_event(StateEvent)
        _LOGGER.debug(
            "Mower clean request: action=%s, cached_state=%s",
            self._args.get("act") if isinstance(self._args, dict) else None,
            state.state.name if state else None,
        )
        result, response = await super()._execute(authenticator, device_info, event_bus)
        _LOGGER.debug(
            "Mower clean result: sent_action=%s, handling=%s",
            self._args.get("act") if isinstance(self._args, dict) else None,
            result.state.name,
        )
        if result.state is HandlingState.SUCCESS:
            # An ACK is not an activity update; ask the device what it is doing.
            event_bus.request_refresh(StateEvent, queue_if_busy=True)
        return result, response

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        return {
            "act": action.value,
            "content": {"type": self._mode.value},
        }


class CleanAreaMower(CleanMower):
    """GOAT mower area clean command.

    Spot-area start sends ``content.type`` ``spotArea`` and ``value``. Pause,
    resume, and stop keep that type and omit ``value``, matching the captured
    stop. App traces do not send a cleaning count.
    """

    def __init__(
        self, mode: CleanMode, area: list[int | float], _cleanings: int = 1
    ) -> None:
        self._mode = mode
        self._area_value = ",".join(str(i) for i in area)
        super().__init__(CleanAction.START)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args["content"]["value"] = self._area_value
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


class GetCleanInfo(OnCleanInfo, JsonCommandWithMessageHandling):
    """Get clean info command."""

    NAME = "getCleanInfo"


class GetCleanInfoV2(GetCleanInfo):
    """Get clean info v2 command."""

    NAME = "getCleanInfo_V2"
