"""Protection state messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.protect_state import ProtectStateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnProtectState(MessageBodyDataDict):
    """Protection state update."""

    NAME = "onProtectState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Notify subscribers without interpreting the boolean states.

        During actual rain, isRainProtect=1 and isRainDelay=0 were observed.
        No semantics are inferred for unobserved transitions or isRainDelay=1.
        """
        event_bus.notify(
            ProtectStateEvent(
                is_anim_protect=bool(data["isAnimProtect"]),
                is_rain_protect=bool(data["isRainProtect"]),
                is_rain_delay=bool(data["isRainDelay"]),
                is_e_stop=bool(data["isEStop"]),
                is_locked=bool(data["isLocked"]),
                is_pin_code=bool(data["isPinCode"]),
                is_prepare_data_success=bool(data["isPrepareDataSuccess"]),
            )
        )
        return HandlingResult.success()
