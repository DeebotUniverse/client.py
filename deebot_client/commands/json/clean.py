"""Clean commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.events.mower import MowingTaskEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json.clean_info import OnCleanInfo, OnScheduleTaskInfo
from deebot_client.models import ApiDeviceInfo, CleanAction, CleanMode, State

from .common import ExecuteCommand, JsonCommandWithMessageHandling
from .schedule_task import SetScheduleTask

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus


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


class GetCleanInfo(OnCleanInfo, JsonCommandWithMessageHandling):
    """Get clean info command."""

    NAME = "getCleanInfo"


class GetCleanInfoV2(GetCleanInfo):
    """Get clean info v2 command."""

    NAME = "getCleanInfo_V2"


class GetScheduleTaskInfo(OnScheduleTaskInfo, JsonCommandWithMessageHandling):
    """Get schedule task info command."""

    NAME = "getScheduleTaskInfo"


class GetCleanInfoMower(GetCleanInfo):
    """Get clean info command for mowers with schedule task info.

    Manual tasks are reported by getCleanInfo, scheduled tasks by getScheduleTaskInfo.
    The other one reports idle, therefore the schedule task info is only requested,
    when getCleanInfo reports idle.
    """

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("state") == "idle" and data.get("trigger") != "alert":
            return HandlingResult(HandlingState.SUCCESS, {_CHECK_SCHEDULE: True})
        return super()._handle_body_data_dict(event_bus, data)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and result.args
            and result.args.get(_CHECK_SCHEDULE)
        ):
            result.requested_commands.append(GetScheduleTaskInfo())
        return result


_CHECK_SCHEDULE = "check_schedule"


class CleanMower(CleanV2):
    """Clean command for newer mowers.

    Uses the command name of the V1 command, but the arguments of the V2 command.
    Pause, resume and stop contain the type of the current task like the app does.
    """

    NAME = "clean"
    _task_type: str = ""

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        """Execute command.

        A scheduled task is paused and resumed with setScheduleTask like the app does.
        """
        task = event_bus.get_last_event(MowingTaskEvent)
        if isinstance(task, MowingTaskEvent) and task.type:
            self._task_type = task.type
            if isinstance(self._args, dict) and self._args["act"] != "start":
                self._args = self._get_args(CleanAction(self._args["act"]))

            if task.scheduled and isinstance(self._args, dict):
                action = CleanAction(self._args["act"])
                state = event_bus.get_last_event(StateEvent)
                if (
                    action == CleanAction.START
                    and isinstance(state, StateEvent)
                    and state.state == State.PAUSED
                ):
                    action = CleanAction.RESUME
                if action in (CleanAction.PAUSE, CleanAction.RESUME):
                    return await SetScheduleTask(action)._execute(  # noqa: SLF001
                        authenticator, device_info, event_bus
                    )

        return await super()._execute(authenticator, device_info, event_bus)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action != CleanAction.START:
            args["content"] = {"type": self._task_type}
        return args


class CleanAreaMower(CleanAreaV2):
    """Clean area command for newer mowers.

    Always starts a new task, also if a task is paused.
    """

    NAME = "clean"

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        """Execute command without converting start into resume."""
        return await super(Clean, self)._execute(authenticator, device_info, event_bus)


class CleanBorderMower(CleanAreaMower):
    """Start the edge (border) mowing of one or more areas.

    Multiple areas are send as "aid:2;aid:1" like the app does.
    """

    def __init__(self, area_ids: list[str] | str) -> None:
        if isinstance(area_ids, str):
            area_ids = [area_ids]
        value = ";".join(f"aid:{area_id}" for area_id in area_ids)
        self._additional_content = {"type": "border", "value": value}
        super(CleanAreaV2, self).__init__(CleanAction.START)
