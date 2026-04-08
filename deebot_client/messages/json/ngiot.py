"""NGIOT numeric-topic MQTT messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.commands.ngiot.battery import GetBattery
from deebot_client.commands.ngiot.child_lock import GetChildLock
from deebot_client.commands.ngiot.clean import GetCleanInfo, map_live_state
from deebot_client.commands.ngiot.map import GetMajorMap, GetMapTrace, GetPos
from deebot_client.commands.ngiot.stats import GetStats
from deebot_client.commands.ngiot.volume import GetVolume
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class OnNgiotMapEvent(MessageBodyDataDict):
    """Handle NGIOT live map/status multiplexed on numeric topic 30000."""

    NAME = "30000"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        handled = False

        if any(key in data for key in ("mapData", "areas", "chargePos")):
            result = GetMajorMap._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        # Live pose-only payloads may arrive without mapData.
        if "pos" in data and "mapData" not in data:
            result = GetPos._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        if "mapTraceData" in data:
            result = GetMapTrace._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        # mapMinorData is confirmed to exist on the live channel, but the current
        # renderer path does not yet support generic NGIOT delta raster application.
        # Log it so captures remain explainable without pretending to render deltas.
        if "mapMinorData" in data:
            _LOGGER.debug(
                "Observed NGIOT live minor-map payload on topic 30000; "
                "generic delta-raster application is not implemented yet"
            )
            handled = True

        return HandlingResult.success() if handled else HandlingResult.analyse()


class OnNgiotStatusEvent(MessageBodyDataDict):
    """Handle NGIOT live status multiplexed on numeric topic 10000."""

    NAME = "10000"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        handled = False

        if "battery" in data:
            result = GetBattery._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        if any(key in data for key in ("cleanArea", "cleanTime", "workMode")):
            result = GetStats._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        if "childLock" in data:
            result = GetChildLock._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        if "volume" in data:
            result = GetVolume._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        live_state = map_live_state(
            data,
            previous=(
                event_bus.get_last_event(StateEvent).state
                if event_bus.get_last_event(StateEvent) is not None
                else None
            ),
        )
        if live_state is not None:
            event_bus.notify(StateEvent(live_state))
            handled = True
        elif any(key in data for key in ("status", "pauseSwitch", "chargeStatus")):
            result = GetCleanInfo._handle_body_data_dict(event_bus, data)
            handled = handled or result.state == HandlingState.SUCCESS

        return HandlingResult.success() if handled else HandlingResult.analyse()