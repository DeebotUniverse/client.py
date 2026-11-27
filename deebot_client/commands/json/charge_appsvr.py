"""Charge command via appsvr/app.do (RobotControl pattern)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from deebot_client.const import PATH_API_APPSVR_APP
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling, _APP_ID, _APP_SIGNATURE

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)


class ChargeAppSvr(JsonCommandWithMessageHandling):
    """Send the robot to its dock via ``RobotControl/Charge`` (``appsvr/app.do``).

    Used by devices whose firmware rejects the standard devmanager ``charge``
    command with ``rcp not support``.
    """

    NAME = "charge_appsvr"

    def _get_payload(self) -> dict[str, Any]:
        """Return empty payload — request is built in ``_execute_api_request``."""
        return {}

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """POST RobotControl/Charge to appsvr/app.do."""
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]
        payload: dict[str, Any] = {
            "app": {
                "id": _APP_ID,
                "signature": _APP_SIGNATURE,
                "ts": int(time.time() * 1000),
            },
            "todo": "RobotControl",
            "did": did,
            "mid": mid,
            "res": res,
            "data": {
                "ctl": {
                    "Charge": {
                        "did": did,
                        "mid": mid,
                        "res": res,
                        "all": False,
                        "type": "p2p",
                        "cmd": "Charge",
                        "data": {"act": "go"},
                    }
                }
            },
        }
        return await authenticator.post_authenticated(PATH_API_APPSVR_APP, payload)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """No-op — response handled in ``_handle_response``."""
        return HandlingResult.success()

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        """Fire RETURNING state on success."""
        if response.get("ret") == "ok":
            event_bus.notify(StateEvent(State.RETURNING))
            return HandlingResult.success()
        _LOGGER.warning("ChargeAppSvr failed: %s", response)
        return HandlingResult(HandlingState.FAILED)
