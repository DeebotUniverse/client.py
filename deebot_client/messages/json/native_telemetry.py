"""Native telemetry parsing (consumables, network, error, stats)."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, TypeGuard

from deebot_client.events import (
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    NetworkInfoEvent,
    StatsEvent,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_NATIVE_LIFESPAN: dict[str, LifeSpan] = {
    "rollBrush": LifeSpan.BRUSH,
    "filter": LifeSpan.FILTER,
    "sideBrush": LifeSpan.SIDE_BRUSH,
    "unitCare": LifeSpan.UNIT_CARE,
}

_NATIVE_ERROR_DESCRIPTIONS: Final = MappingProxyType(
    {0: "No error", 102: "Robot is lifted", 111: "Bumper is stuck"}
)


def _is_number(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def handle_consumables(event_bus: EventBus, value: Any) -> None:
    """Notify lifespan events for known consumables, skipping invalid entries."""
    if not isinstance(value, list):
        return
    for entry in value:
        if not isinstance(entry, dict):
            continue
        raw_type = entry.get("type")
        component = (
            _NATIVE_LIFESPAN.get(raw_type) if isinstance(raw_type, str) else None
        )
        left = entry.get("left")
        total = entry.get("total")
        if component is None or not _is_number(left) or not _is_number(total):
            continue
        if total <= 0 or left < 0:
            continue
        percent = round(float(left) / float(total) * 100, 2)
        event_bus.notify(LifeSpanEvent(component, percent, int(left)))


def handle_device_info(event_bus: EventBus, value: Any) -> None:
    """Notify network event, merging partial updates with prior fields."""
    if not isinstance(value, dict):
        return
    last = event_bus.get_last_event(NetworkInfoEvent)
    if not isinstance(last, NetworkInfoEvent):
        last = None

    ip = value.get("ip")
    ip = ip if isinstance(ip, str) else (last.ip if last else None)
    ssid = value.get("ssid")
    ssid = ssid if isinstance(ssid, str) else (last.ssid if last else None)
    mac = value.get("mac")
    mac = mac if isinstance(mac, str) else (last.mac if last else None)

    rssi: int | None = None
    raw_rssi = value.get("rssi")
    if raw_rssi is not None and not isinstance(raw_rssi, bool):
        try:
            rssi = int(float(raw_rssi))
        except TypeError, ValueError:
            rssi = None
    if rssi is None and last is not None:
        rssi = last.rssi

    if ip is None or ssid is None or mac is None or rssi is None:
        return
    event_bus.notify(NetworkInfoEvent(ip=ip, ssid=ssid, rssi=rssi, mac=mac))


def handle_error(event_bus: EventBus, value: Any) -> None:
    """Emit confirmed native descriptions; empty lists explicitly clear errors."""
    if not isinstance(value, list):
        return
    code = value[-1] if value else 0
    if isinstance(code, bool) or not isinstance(code, int):
        return
    event_bus.notify(ErrorEvent(code, _NATIVE_ERROR_DESCRIPTIONS.get(code)))


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def handle_clean_stats(
    event_bus: EventBus, data: dict[str, Any], *, seconds_per_unit: int = 60
) -> None:
    """Merge native stats; 10000 uses minutes, completion analytics uses seconds."""
    area = _non_negative_int(data.get("cleanArea"))
    duration = _non_negative_int(data.get("cleanTime"))
    if area is None and duration is None:
        return
    last = event_bus.get_last_event(StatsEvent)
    if not isinstance(last, StatsEvent):
        last = None
    event_bus.notify(
        StatsEvent(
            area=area if area is not None else (last.area if last else None),
            time=(
                duration * seconds_per_unit
                if duration is not None
                else (last.time if last else None)
            ),
            type=last.type if last else None,
        )
    )
