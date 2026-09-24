"""Clean command via appsvr/app.do and ngiot (RobotControl pattern)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import aiohttp

from deebot_client.const import PATH_API_APPSVR_APP
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import CleanAction, State

from .common import (
    JsonCommandWithMessageHandling,
    _APP_ID,
    _APP_SIGNATURE,
    get_sst,
    ngiot_post,
)

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)


class CleanAppSvr(JsonCommandWithMessageHandling):
    """Handle all clean actions for devices using the appsvr/ngiot pattern.

    * ``START`` → ``RobotControl/Clean`` via ``appsvr/app.do``
    * ``PAUSE`` / ``STOP`` → ngiot ``apn=40009``
    * ``RESUME`` → ngiot ``apn=40011``

    Used by devices whose firmware rejects the standard devmanager ``clean``
    command with ``rcp not support``.
    """

    NAME = "clean_appsvr"

    def __init__(self, action: CleanAction) -> None:
        """Initialise with the desired clean action."""
        self._action = action
        super().__init__()

    def _get_payload(self) -> dict[str, Any]:
        """Return empty payload — request is built in ``_execute_api_request``."""
        return {}

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """Route to appsvr/app.do or ngiot depending on the action."""
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]

        if self._action == CleanAction.START:
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
                        "Clean": {
                            "did": did,
                            "mid": mid,
                            "res": res,
                            "all": False,
                            "type": "p2p",
                            "cmd": "Clean",
                            "data": {"act": "s", "type": "auto", "tri": "app"},
                        }
                    }
                },
            }
            return await authenticator.post_authenticated(PATH_API_APPSVR_APP, payload)

        credentials = await authenticator.authenticate()
        async with aiohttp.ClientSession() as session:
            sst = await get_sst(
                session,
                token=credentials.token,
                user_id=credentials.user_id,
                did=did,
                mid=mid,
            )
            if self._action == CleanAction.RESUME:
                resp = await ngiot_post(
                    session,
                    sst=sst, eid=did, et=mid, er=res,
                    apn="40011",
                    body_data={"pauseSwitch": False},
                )
            else:
                resp = await ngiot_post(
                    session,
                    sst=sst, eid=did, et=mid, er=res,
                    apn="40009",
                    body_data={"pauseSwitch": True},
                )
        return {"ret": "ok", "ngiot": resp}

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """No-op — response handled in ``_handle_response``."""
        return HandlingResult.success()

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        """Fire the appropriate state event on success."""
        if response.get("ret") == "ok":
            if self._action in (CleanAction.START, CleanAction.RESUME):
                event_bus.notify(StateEvent(State.CLEANING))
            else:
                event_bus.notify(StateEvent(State.PAUSED))
            return HandlingResult.success()
        _LOGGER.warning("CleanAppSvr failed: %s", response)
        return HandlingResult(HandlingState.FAILED)
