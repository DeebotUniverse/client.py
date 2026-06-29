"""Commands for DEEBOT NEO 2.0 (device class eyfj07).

This device uses non-standard API patterns:
- Status: single combined command ``10001`` via devmanager.do
- Clean/Charge: ``RobotControl`` via ``appsvr/app.do``
- Pause/Resume/FanSpeed: ``ngiot`` endpoint with SST bearer auth

All patterns were reverse-engineered from live mitmproxy captures of the
official Ecovacs app (AU region) and confirmed against a physical robot.
"""

from __future__ import annotations

import secrets
import time
from typing import TYPE_CHECKING, Any, ClassVar

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
from deebot_client.events.water_info import MopAttachedEvent, WaterAmount, WaterAmountEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import CleanAction, State
from deebot_client.util import get_enum

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)

_SST_URL = "https://api-base.dc-na.ww.ecouser.net/api/new-perm/token/sst/issue"
_NGIOT_URL = "https://api-ngiot.dc-na.ww.ecouser.net/api/iot/endpoint/control"

# Static signature block required by appsvr/app.do — server does not validate
# the signature value, so a fixed string is acceptable here.
_APP_ID = "ecovacs"
_APP_SIGNATURE = "f66440b16af096f33575d1e396eab38e93991cc8"  # noqa: S105


# ---------------------------------------------------------------------------
# Internal HTTP helpers
# ---------------------------------------------------------------------------


async def _get_sst(
    session: aiohttp.ClientSession,
    *,
    token: str,
    user_id: str,
    did: str,
    mid: str,
) -> str:
    """Obtain a Service Session Token (SST) for ngiot control commands."""
    body = {
        "acl": [
            {
                "policy": [{"obj": [f"Endpoint:{mid}:{did}"], "perms": ["Control"]}],
                "svc": "dim",
            }
        ],
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
    return data["data"]["data"]["token"]  # type: ignore[no-any-return]


async def _ngiot_post(
    session: aiohttp.ClientSession,
    *,
    sst: str,
    eid: str,
    et: str,
    er: str,
    apn: str,
    body_data: dict[str, Any],
) -> dict[str, Any]:
    """POST a command to the ngiot endpoint/control API."""
    si = secrets.token_urlsafe(12)[:16]
    reqid = secrets.token_urlsafe(6)[:6]
    params = {"si": si, "ct": "q", "eid": eid, "et": et, "er": er, "apn": apn, "fmt": "j"}
    payload: dict[str, Any] = {
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
        return await resp.json(content_type=None) if text.strip() else {}  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Field / value mappings (all derived from live captures)
# ---------------------------------------------------------------------------

_ALL_STATUS_FIELDS: list[str] = [
    "stationType", "stationStatus", "cleanValues", "chargeStatus",
    "pauseSwitch", "battery", "disturbSwitch", "disturbTimeSet",
    "mopState", "workMode", "breakCleanStatus", "fanMode", "waterMode",
    "cleanCount", "error", "consumables", "newMapReport",
    "expandedMapReport", "cleanLogReport", "deviceInfo", "childLock",
    "isEurope", "cleanTime", "cleanArea", "silentOtaSwitch",
    "nextSchedule", "dormant", "relocateSwitch", "unitSet", "otaData",
    "voiceData", "timeZone",
]

# Maps firmware consumable type strings to LifeSpan enum values.
# "rollBrush" → BRUSH and "filter" → FILTER are manual mappings because
# the firmware strings do not match LifeSpan.value directly.
_CONSUMABLE_MAP: dict[str, LifeSpan] = {
    "sideBrush": LifeSpan.SIDE_BRUSH,
    "unitCare": LifeSpan.UNIT_CARE,
    "rollBrush": LifeSpan.BRUSH,
    "filter": LifeSpan.FILTER,
}

# Maps firmware fanMode strings to FanSpeedLevel.
# "max" (MAX_PLUS) confirmed from capture; others inferred from app labels.
_FAN_MODE_MAP: dict[str, FanSpeedLevel] = {
    "quiet": FanSpeedLevel.QUIET,
    "standard": FanSpeedLevel.NORMAL,
    "strong": FanSpeedLevel.MAX,
    "max": FanSpeedLevel.MAX_PLUS,   # CONFIRMED from capture
    "auto": FanSpeedLevel.NORMAL,    # fallback; not independently confirmed
}

# Maps FanSpeedLevel back to the firmware string used by the set command.
_FAN_LEVEL_TO_MODE: dict[FanSpeedLevel, str] = {
    FanSpeedLevel.QUIET: "quiet",
    FanSpeedLevel.NORMAL: "standard",
    FanSpeedLevel.MAX: "strong",
    FanSpeedLevel.MAX_PLUS: "max",
}

# Maps firmware waterMode strings to WaterAmount.
# "low" confirmed from capture; others inferred from naming pattern.
_WATER_MODE_MAP: dict[str, WaterAmount] = {
    "low": WaterAmount.LOW,          # CONFIRMED from capture
    "medium": WaterAmount.MEDIUM,    # inferred
    "high": WaterAmount.HIGH,        # inferred
    "ultrahigh": WaterAmount.ULTRAHIGH,  # inferred
}


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


class GetCombinedStatus(JsonCommandWithMessageHandling):
    """Get all device status fields in a single combined call (cmdName ``10001``).

    This firmware does not respond to the standard individual commands
    (``getBattery``, ``getChargeState``, ``getCleanInfo``, etc.) with real
    data — they all return ``{"code": 0, "data": None}``.  Instead, one
    combined command returns battery, charge state, clean state, fan speed,
    consumables, and more in a single response.

    A short-lived class-level cache (keyed by device id) avoids redundant
    network calls when multiple capabilities request a refresh within the
    same poll cycle.
    """

    NAME = "10001"
    CACHE_SECONDS = 5.0

    _cache: ClassVar[dict[str, tuple[float, dict[str, Any]]]] = {}

    def __init__(
        self,
        fields: list[str] | None = None,
        *,
        is_available_check: bool = False,
    ) -> None:
        """Initialise the command, optionally restricting the requested fields."""
        if fields is None:
            fields = _ALL_STATUS_FIELDS
        self._is_available_check = is_available_check
        super().__init__({"fields": fields})

    def _get_payload(self) -> dict[str, Any]:
        """Build payload matching the real app's captured header format.

        The generic ``JsonCommand`` header (``pri``/``ts``/``tzm``/``ver``
        only) receives no response from this firmware — likely because it
        does not resemble a legitimate app request.  This mirrors the real
        captured header as closely as possible.
        """
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

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """Execute the API request, reusing a cached response when available."""
        device_id = device_info.get("did", "")
        now = time.monotonic()
        cached = GetCombinedStatus._cache.get(device_id)
        if cached is not None:
            cached_time, cached_response = cached
            if now - cached_time < self.CACHE_SECONDS:
                _LOGGER.debug(
                    "GetCombinedStatus: reusing cached response (%.1fs old)",
                    now - cached_time,
                )
                return cached_response

        response = await super()._execute_api_request(authenticator, device_info)
        GetCombinedStatus._cache[device_id] = (now, response)
        return response

    @classmethod
    def _handle_body(
        cls,
        event_bus: EventBus,
        body: dict[str, Any],
    ) -> HandlingResult:
        """Parse the combined status response and fire events for known fields."""
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
            # workMode="auto" → cleaning; workMode="stop" → idle.
            # cleanTime=0 even at the very start of a clean cycle, so it
            # is NOT a reliable cleaning indicator.
            state = State.CLEANING if work_mode and work_mode != "stop" else State.IDLE

        if state is not None:
            _LOGGER.debug(
                "NEO2 state: %s (chargeStatus=%s pauseSwitch=%s workMode=%s error=%s)",
                state, charge_status, pause_switch, work_mode, error_list,
            )
            event_bus.notify(StateEvent(state))

        consumables = data.get("consumables")
        if isinstance(consumables, list):
            for item in consumables:
                item_type = item.get("type")
                life_span_type = _CONSUMABLE_MAP.get(item_type)
                if life_span_type is None:
                    _LOGGER.debug(
                        "Unmapped consumable type %r — skipping LifeSpanEvent", item_type
                    )
                    continue
                left = item.get("left")
                total = item.get("total")
                if left is None or total is None or total == 0:
                    continue
                event_bus.notify(
                    LifeSpanEvent(
                        type=life_span_type,
                        percent=(left / total) * 100,
                        remaining=int(left),
                    )
                )

        if isinstance(error_list, list) and error_list:
            error_code = error_list[0]
            event_bus.notify(
                ErrorEvent(
                    code=error_code,
                    description="No error" if error_code == 0 else None,
                )
            )

        fan_mode = data.get("fanMode")
        if fan_mode is not None:
            fan_level = _FAN_MODE_MAP.get(fan_mode)
            if fan_level is not None:
                event_bus.notify(FanSpeedEvent(fan_level))
            else:
                _LOGGER.debug("Unmapped fanMode %r — skipping FanSpeedEvent", fan_mode)

        water_mode = data.get("waterMode")
        if water_mode is not None:
            water_amount = _WATER_MODE_MAP.get(water_mode)
            if water_amount is not None:
                event_bus.notify(WaterAmountEvent(water_amount))
            else:
                _LOGGER.debug("Unmapped waterMode %r — skipping WaterAmountEvent", water_mode)

        mop_state = data.get("mopState")
        if mop_state is not None:
            if mop_state == "none":
                event_bus.notify(MopAttachedEvent(attached=False))
            else:
                # Any value other than "none" is treated as mop attached.
                # Only "none" has been confirmed from captures; the exact
                # string for "attached" is not yet known.
                _LOGGER.debug("mopState=%r — treating as mop attached", mop_state)
                event_bus.notify(MopAttachedEvent(attached=True))

        child_lock = data.get("childLock")
        if child_lock is not None:
            event_bus.notify(ChildLockEvent(enabled=bool(child_lock)))

        ota_data = data.get("otaData")
        silent_ota_switch = data.get("silentOtaSwitch")
        if ota_data is not None or silent_ota_switch is not None:
            ota_info = (ota_data or {}).get("otaInfo") or {}
            version = ota_info.get("ver") or None
            event_bus.notify(
                OtaEvent(
                    support_auto=True,
                    auto_enabled=silent_ota_switch,
                    version=version if version else None,
                    status=(ota_data or {}).get("otaStatus"),
                    progress=ota_info.get("progress"),
                )
            )

        return HandlingResult.success()


# ---------------------------------------------------------------------------
# Action commands
# ---------------------------------------------------------------------------


class _Neo2ActionBase(JsonCommandWithMessageHandling):
    """Base for NEO 2.0 action commands.

    Subclasses override ``_execute_api_request`` to use either the
    ``appsvr/app.do`` (RobotControl) or ``ngiot`` endpoint, then call
    ``_on_success`` to fire the appropriate state event.
    """

    # Required by Command.__init_subclass__ even on abstract bases.
    NAME = "_neo2_base"
    DATA_TYPE = DataType.JSON

    def _get_payload(self) -> dict[str, Any]:
        """Return an empty payload (not used — subclasses build their own)."""
        return {}

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """No-op body handler — response is handled in ``_handle_response``."""
        return HandlingResult.success()

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        """Check ``ret=ok`` and fire the appropriate state event on success."""
        if response.get("ret") == "ok":
            self._on_success(event_bus)
            return HandlingResult.success()
        _LOGGER.warning("%s failed: %s", self.NAME, response)
        return HandlingResult(HandlingState.FAILED)

    def _on_success(self, event_bus: EventBus) -> None:
        """Fire state events after a successful command; override in subclasses."""


class Neo2Charge(_Neo2ActionBase):
    """Send the robot to its dock via ``RobotControl/Charge`` (``appsvr/app.do``)."""

    NAME = "neo2_charge"

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

    def _on_success(self, event_bus: EventBus) -> None:
        """Fire RETURNING state after a successful charge command."""
        event_bus.notify(StateEvent(State.RETURNING))


class Neo2Clean(_Neo2ActionBase):
    """Handle all clean actions for the NEO 2.0.

    * ``START`` → ``RobotControl/Clean`` via ``appsvr/app.do``
    * ``PAUSE`` / ``STOP`` → ngiot ``apn=40009`` (pause)
    * ``RESUME`` → ngiot ``apn=40011`` (resume)
    """

    NAME = "neo2_clean"

    def __init__(self, action: CleanAction) -> None:
        """Initialise with the desired clean action."""
        self._action = action
        super().__init__()

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
            sst = await _get_sst(
                session,
                token=credentials.token,
                user_id=credentials.user_id,
                did=did,
                mid=mid,
            )
            if self._action == CleanAction.RESUME:
                resp = await _ngiot_post(
                    session,
                    sst=sst, eid=did, et=mid, er=res,
                    apn="40011",
                    body_data={"pauseSwitch": False},
                )
            else:  # PAUSE or STOP both map to pause
                resp = await _ngiot_post(
                    session,
                    sst=sst, eid=did, et=mid, er=res,
                    apn="40009",
                    body_data={"pauseSwitch": True},
                )
        return {"ret": "ok", "ngiot": resp}

    def _on_success(self, event_bus: EventBus) -> None:
        """Fire the appropriate state event for the action taken."""
        if self._action in (CleanAction.START, CleanAction.RESUME):
            event_bus.notify(StateEvent(State.CLEANING))
        else:
            event_bus.notify(StateEvent(State.PAUSED))


class Neo2SetFanSpeed(_Neo2ActionBase):
    """Set fan speed via ngiot ``apn=50011``.

    Fan speed modes confirmed from captures:
    * ``"max"`` (MAX_PLUS) — confirmed
    * ``"quiet"``, ``"standard"``, ``"strong"`` — inferred from app labels
    """

    NAME = "neo2_set_fan_speed"

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        """Initialise with the desired fan speed level."""
        if isinstance(speed, str):
            speed = get_enum(FanSpeedLevel, speed)
        self._speed = speed
        super().__init__()

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """POST the fan speed change to the ngiot endpoint."""
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]
        fan_mode = _FAN_LEVEL_TO_MODE.get(self._speed, "standard")

        credentials = await authenticator.authenticate()
        async with aiohttp.ClientSession() as session:
            sst = await _get_sst(
                session,
                token=credentials.token,
                user_id=credentials.user_id,
                did=did,
                mid=mid,
            )
            resp = await _ngiot_post(
                session,
                sst=sst, eid=did, et=mid, er=res,
                apn="50011",
                body_data={"fanMode": fan_mode},
            )
        return {"ret": "ok", "ngiot": resp}

    def _on_success(self, event_bus: EventBus) -> None:
        """Fire FanSpeedEvent after a successful speed change."""
        event_bus.notify(FanSpeedEvent(self._speed))
