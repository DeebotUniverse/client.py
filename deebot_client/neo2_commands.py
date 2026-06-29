"""Custom commands for DEEBOT NEO 2.0 (eyfj07).

These commands implement the non-standard API patterns required by this device:
- Status: uses combined command "10001" via devmanager.do
- Clean/Charge: RobotControl commands via appsvr/app.do
- Pause/Resume: ngiot endpoint/control with SST auth
- Fan speed: ngiot endpoint/control with SST auth
"""
from __future__ import annotations

import secrets
import time
from typing import TYPE_CHECKING, Any

import aiohttp

from deebot_client.commands.json.common import JsonCommandWithMessageHandling
from deebot_client.const import DataType, PATH_API_APPSVR_APP
from deebot_client.events import (
    BatteryEvent,
    ChildLockEvent,
    ErrorEvent,
    FanSpeedEvent,
    LifeSpan,
    LifeSpanEvent,
    OtaEvent,
    StateEvent,
)
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.events import water_info
from deebot_client.events.water_info import MopAttachedEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import CleanAction, State

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)

_APP_BLOCK = {
    "id": "ecovacs",
    "signature": "f66440b16af096f33575d1e396eab38e93991cc8",
    "ts": 0,
}

_SST_URL = "https://api-base.dc-na.ww.ecouser.net/api/new-perm/token/sst/issue"
_NGIOT_URL = "https://api-ngiot.dc-na.ww.ecouser.net/api/iot/endpoint/control"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_sst(session: aiohttp.ClientSession, *, token: str, user_id: str, did: str, mid: str) -> str:
    """Obtain a Service Session Token for ngiot control commands."""
    body = {
        "acl": [{"policy": [{"obj": [f"Endpoint:{mid}:{did}"], "perms": ["Control"]}], "svc": "dim"}],
        "exp": 600,
        "sub": user_id,
    }
    headers = {
        "authorization": f"Bearer {token}",
        "x-eco-request-id": secrets.token_hex(16),
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/4.9.1",
    }
    async with session.post(_SST_URL, json=body, headers=headers) as resp:
        data = await resp.json(content_type=None)
    return data["data"]["data"]["token"]


async def _ngiot_post(session: aiohttp.ClientSession, *, sst: str, eid: str, et: str, er: str, apn: str, body_data: dict) -> dict:
    """POST a command to the ngiot endpoint/control API."""
    si = secrets.token_urlsafe(12)[:16]
    reqid = secrets.token_urlsafe(6)[:6]
    params = {"si": si, "ct": "q", "eid": eid, "et": et, "er": er, "apn": apn, "fmt": "j"}
    payload = {
        "body": {"data": body_data},
        "header": {
            "channel": "Android",
            "m": "request",
            "pri": 2,
            "reqid": reqid,
            "ts": str(int(time.time() * 1000)),
            "tzc": "Australia/Melbourne",
            "tzm": 600,
            "ver": "0.0.22",
        },
    }
    headers = {
        "authorization": f"Bearer {sst}",
        "appid": "ecovacs",
        "x-eco-request-id": reqid,
        "content-type": "application/json",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/4.9.1",
    }
    async with session.post(_NGIOT_URL, json=payload, params=params, headers=headers) as resp:
        text = await resp.text()
        _LOGGER.debug("ngiot apn=%s HTTP %s body=%r", apn, resp.status, text)
        return await resp.json(content_type=None) if text.strip() else {}


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

_ALL_STATUS_FIELDS = [
    "stationType", "stationStatus", "cleanValues", "chargeStatus",
    "pauseSwitch", "battery", "disturbSwitch", "disturbTimeSet",
    "mopState", "workMode", "breakCleanStatus", "fanMode", "waterMode",
    "cleanCount", "error", "consumables", "newMapReport",
    "expandedMapReport", "cleanLogReport", "deviceInfo", "childLock",
    "isEurope", "cleanTime", "cleanArea", "silentOtaSwitch",
    "nextSchedule", "dormant", "relocateSwitch", "unitSet", "otaData",
    "voiceData", "timeZone",
]

_CONSUMABLE_TYPE_MAP: dict[str, LifeSpan] = {
    "sideBrush": LifeSpan.SIDE_BRUSH,
    "unitCare": LifeSpan.UNIT_CARE,
    "rollBrush": LifeSpan.BRUSH,
    "filter": LifeSpan.FILTER,
}

_FAN_MODE_MAP: dict[str, FanSpeedLevel] = {
    "quiet": FanSpeedLevel.QUIET,
    "standard": FanSpeedLevel.NORMAL,
    "strong": FanSpeedLevel.MAX,
    "max": FanSpeedLevel.MAX_PLUS,
    "auto": FanSpeedLevel.NORMAL,
}

_WATER_MODE_MAP: dict[str, water_info.WaterAmount] = {
    "low": water_info.WaterAmount.LOW,
    "medium": water_info.WaterAmount.MEDIUM,
    "high": water_info.WaterAmount.HIGH,
    "ultrahigh": water_info.WaterAmount.ULTRAHIGH,
}


class GetCombinedStatus(JsonCommandWithMessageHandling):
    """Get combined status for NEO 2.0 via cmdName '10001'.

    This single command returns battery, charge state, clean state,
    fan speed, water amount, consumables, and more. All status
    capabilities share this command with a short-lived response cache
    to avoid redundant network calls within one poll cycle.
    """

    NAME = "10001"
    CACHE_SECONDS = 5.0

    _cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def __init__(self, fields: list[str] | None = None, *, is_available_check: bool = False) -> None:
        if fields is None:
            fields = _ALL_STATUS_FIELDS
        self._is_available_check = is_available_check
        super().__init__({"fields": fields})

    def _get_payload(self) -> dict[str, Any]:
        return {
            "header": {
                "channel": "iOS",
                "reqid": "neo2py",
                "ts": str(int(time.time() * 1000)),
                "ver": "0.0.50",
                "m": "request",
                "pri": 1,
                "tzm": 600,
                "tzc": "Australia/Melbourne",
            },
            "body": {"data": self._args},
        }

    async def _execute_api_request(self, authenticator: Authenticator, device_info: ApiDeviceInfo) -> dict[str, Any]:
        device_id = device_info.get("did", "")
        now = time.monotonic()
        cached = GetCombinedStatus._cache.get(device_id)
        if cached is not None:
            cached_time, cached_response = cached
            if now - cached_time < self.CACHE_SECONDS:
                _LOGGER.debug("GetCombinedStatus: reusing cached response (%.1fs old)", now - cached_time)
                return cached_response

        response = await super()._execute_api_request(authenticator, device_info)
        GetCombinedStatus._cache[device_id] = (now, response)
        return response

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        data = body.get("data")
        if not isinstance(data, dict):
            return HandlingResult(HandlingState.ANALYSE)

        _LOGGER.debug("GetCombinedStatus data: %s", data)

        if "battery" in data and data["battery"] is not None:
            event_bus.notify(BatteryEvent(data["battery"]))

        charge_status = data.get("chargeStatus")
        pause_switch = data.get("pauseSwitch")
        error_list = data.get("error")
        work_mode = data.get("workMode")

        state: State | None = None
        if error_list and error_list != [0]:
            state = State.ERROR
        elif charge_status is True:
            state = State.DOCKED
        elif pause_switch is True:
            state = State.PAUSED
        elif charge_status is False:
            state = State.CLEANING if work_mode and work_mode != "stop" else State.IDLE

        if state is not None:
            _LOGGER.debug("NEO2 state: %s (chargeStatus=%s pauseSwitch=%s workMode=%s error=%s)",
                          state, charge_status, pause_switch, work_mode, error_list)
            event_bus.notify(StateEvent(state))

        consumables = data.get("consumables")
        if isinstance(consumables, list):
            for item in consumables:
                item_type = item.get("type")
                life_span_type = _CONSUMABLE_TYPE_MAP.get(item_type)
                if life_span_type is None:
                    continue
                left = item.get("left")
                total = item.get("total")
                if left is None or total is None or total == 0:
                    continue
                event_bus.notify(LifeSpanEvent(type=life_span_type, percent=(left / total) * 100, remaining=int(left)))

        if isinstance(error_list, list) and error_list:
            error_code = error_list[0]
            description = "No error" if error_code == 0 else None
            event_bus.notify(ErrorEvent(code=error_code, description=description))

        fan_mode = data.get("fanMode")
        if fan_mode is not None:
            fan_level = _FAN_MODE_MAP.get(fan_mode)
            if fan_level is not None:
                event_bus.notify(FanSpeedEvent(fan_level))

        water_mode = data.get("waterMode")
        if water_mode is not None:
            water_amount = _WATER_MODE_MAP.get(water_mode)
            if water_amount is not None:
                event_bus.notify(water_info.WaterAmountEvent(water_amount))

        mop_state = data.get("mopState")
        if mop_state is not None:
            if mop_state == "none":
                event_bus.notify(MopAttachedEvent(False))
            else:
                _LOGGER.debug("mopState=%s (unknown — may indicate mop attached)", mop_state)
                event_bus.notify(MopAttachedEvent(True))

        child_lock = data.get("childLock")
        if child_lock is not None:
            event_bus.notify(ChildLockEvent(enabled=bool(child_lock)))

        ota_data = data.get("otaData")
        silent_ota_switch = data.get("silentOtaSwitch")
        if ota_data is not None or silent_ota_switch is not None:
            ota_info = (ota_data or {}).get("otaInfo") or {}
            version = ota_info.get("ver") or None
            progress = ota_info.get("progress")
            status = (ota_data or {}).get("otaStatus")
            event_bus.notify(OtaEvent(
                support_auto=True,
                auto_enabled=silent_ota_switch,
                version=version if version else None,
                status=status,
                progress=progress,
            ))

        return HandlingResult.success()


# ---------------------------------------------------------------------------
# Action commands
# ---------------------------------------------------------------------------

class _Neo2ActionBase(JsonCommandWithMessageHandling):
    """Base for NEO 2.0 action commands that override the full execute path."""

    NAME = "_neo2_base"
    DATA_TYPE = DataType.JSON

    def _get_payload(self) -> dict[str, Any]:
        return {}

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        return HandlingResult.success()

    def _handle_response(self, event_bus: EventBus, response: dict[str, Any]) -> HandlingResult:
        if response.get("ret") == "ok":
            self._on_success(event_bus)
            return HandlingResult.success()
        _LOGGER.warning("%s failed: %s", self.NAME, response)
        return HandlingResult(HandlingState.FAILED)

    def _on_success(self, event_bus: EventBus) -> None:
        pass


class Neo2Charge(_Neo2ActionBase):
    """Send robot to dock via RobotControl/Charge (appsvr/app.do)."""

    NAME = "neo2_charge"

    async def _execute_api_request(self, authenticator: Authenticator, device_info: ApiDeviceInfo) -> dict[str, Any]:
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]
        payload = {
            "app": {**_APP_BLOCK, "ts": int(time.time() * 1000)},
            "todo": "RobotControl",
            "did": did, "mid": mid, "res": res,
            "data": {"ctl": {"Charge": {
                "did": did, "mid": mid, "res": res,
                "all": False, "type": "p2p", "cmd": "Charge",
                "data": {"act": "go"},
            }}},
        }
        return await authenticator.post_authenticated(PATH_API_APPSVR_APP, payload)

    def _on_success(self, event_bus: EventBus) -> None:
        event_bus.notify(StateEvent(State.RETURNING))


class Neo2Clean(_Neo2ActionBase):
    """Handle all clean actions for NEO 2.0.

    START → RobotControl/Clean via appsvr/app.do
    PAUSE/STOP → ngiot apn=40009
    RESUME → ngiot apn=40011
    """

    NAME = "neo2_clean"

    def __init__(self, action: CleanAction) -> None:
        self._action = action
        super().__init__()

    async def _execute_api_request(self, authenticator: Authenticator, device_info: ApiDeviceInfo) -> dict[str, Any]:
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]

        if self._action == CleanAction.START:
            payload = {
                "app": {**_APP_BLOCK, "ts": int(time.time() * 1000)},
                "todo": "RobotControl",
                "did": did, "mid": mid, "res": res,
                "data": {"ctl": {"Clean": {
                    "did": did, "mid": mid, "res": res,
                    "all": False, "type": "p2p", "cmd": "Clean",
                    "data": {"act": "s", "type": "auto", "tri": "app"},
                }}},
            }
            return await authenticator.post_authenticated(PATH_API_APPSVR_APP, payload)

        # PAUSE and STOP both use ngiot pause
        credentials = await authenticator.authenticate()
        async with aiohttp.ClientSession() as session:
            sst = await _get_sst(session, token=credentials.token, user_id=credentials.user_id, did=did, mid=mid)
            if self._action == CleanAction.RESUME:
                resp = await _ngiot_post(session, sst=sst, eid=did, et=mid, er=res, apn="40011", body_data={"pauseSwitch": False})
            else:  # PAUSE or STOP
                resp = await _ngiot_post(session, sst=sst, eid=did, et=mid, er=res, apn="40009", body_data={"pauseSwitch": True})
        return {"ret": "ok", "ngiot": resp}

    def _on_success(self, event_bus: EventBus) -> None:
        if self._action == CleanAction.START:
            event_bus.notify(StateEvent(State.CLEANING))
        elif self._action == CleanAction.RESUME:
            event_bus.notify(StateEvent(State.CLEANING))
        else:
            event_bus.notify(StateEvent(State.PAUSED))


class Neo2SetFanSpeed(_Neo2ActionBase):
    """Set fan speed via ngiot apn=50011."""

    NAME = "neo2_set_fan_speed"

    _LEVEL_TO_MODE: dict[FanSpeedLevel, str] = {
        FanSpeedLevel.QUIET: "quiet",
        FanSpeedLevel.NORMAL: "standard",
        FanSpeedLevel.MAX: "strong",
        FanSpeedLevel.MAX_PLUS: "max",
    }

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        if isinstance(speed, str):
            from deebot_client.util import get_enum
            speed = get_enum(FanSpeedLevel, speed)
        self._speed = speed
        super().__init__()

    async def _execute_api_request(self, authenticator: Authenticator, device_info: ApiDeviceInfo) -> dict[str, Any]:
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]
        fan_mode = self._LEVEL_TO_MODE.get(self._speed, "standard")

        credentials = await authenticator.authenticate()
        async with aiohttp.ClientSession() as session:
            sst = await _get_sst(session, token=credentials.token, user_id=credentials.user_id, did=did, mid=mid)
            resp = await _ngiot_post(session, sst=sst, eid=did, et=mid, er=res, apn="50011", body_data={"fanMode": fan_mode})
        return {"ret": "ok", "ngiot": resp}

    def _on_success(self, event_bus: EventBus) -> None:
        event_bus.notify(FanSpeedEvent(self._speed))
