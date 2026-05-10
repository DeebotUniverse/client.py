"""Inspect cached map and room events for one device."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from typing import TYPE_CHECKING, Any

import aiohttp
import orjson

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.commands.json.map import GetCachedMapInfo
from deebot_client.const import AUTH_DOMAIN_ECOVACS
from deebot_client.device import Device
from deebot_client.events import MapSetType, RoomsEvent
from deebot_client.events.map import CachedMapInfoEvent, Map, MapInfoEvent
from deebot_client.rs.util import decompress_base64_data
from deebot_client.util import md5

if TYPE_CHECKING:
    from deebot_client.command import DeviceCommandResult
    from deebot_client.models import DeviceInfo


def _select_device(devices: list[DeviceInfo]) -> DeviceInfo:
    device_class = os.environ.get("ECOVACS_DEVICE_CLASS")
    device_nick = os.environ.get("ECOVACS_DEVICE_NICK")

    for device in devices:
        if device_class and device.api["class"] != device_class:
            continue
        if device_nick and device.api.get("nick") != device_nick:
            continue
        return device

    selectors = {
        "class": device_class,
        "nick": device_nick,
    }
    msg = f"No MQTT device matched selectors: {selectors}"
    raise ValueError(msg)


def _map_summary(map_info: Map) -> dict[str, object]:
    return {
        "id": map_info.id,
        "name": map_info.name,
        "using": map_info.using,
        "built": map_info.built,
        "angle": str(map_info.angle),
    }


def _summarize_rooms_event(event: RoomsEvent | None) -> dict[str, object] | None:
    if event is None:
        return None

    return {
        "map_id": event.map_id,
        "room_count": len(event.rooms),
        "rooms": [
            {"id": room.id, "name": room.name}
            for room in sorted(event.rooms, key=lambda room: room.id)
        ],
    }


def _body_data(result: DeviceCommandResult) -> dict[str, Any] | None:
    response = result.raw_response
    payload = response.get("resp", response)
    body = payload.get("body") if isinstance(payload, dict) else None
    data = body.get("data") if isinstance(body, dict) else None
    return data if isinstance(data, dict) else None


def _summarize_map_set_response(result: DeviceCommandResult) -> dict[str, object]:
    response = result.raw_response
    payload = response.get("resp", response)
    body = payload.get("body") if isinstance(payload, dict) else None
    summary: dict[str, object] = {"device_reached": result.device_reached}

    if isinstance(body, dict):
        summary["body_code"] = body.get("code")
        summary["body_msg"] = body.get("msg")

    data = _body_data(result)
    if data is None:
        return {key: value for key, value in summary.items() if value is not None}

    summary["map_id"] = data.get("mid")
    summary["type"] = data.get("type")

    compressed_subsets = data.get("subsets")
    if isinstance(compressed_subsets, str):
        subsets = orjson.loads(decompress_base64_data(compressed_subsets).decode())
        if isinstance(subsets, list):
            summary["subset_count"] = len(subsets)
            if subsets and isinstance(subsets[0], list):
                subset_lengths = sorted(
                    {len(subset) for subset in subsets if isinstance(subset, list)}
                )
                first_subset_length = len(subsets[0])
                summary["subset_lengths"] = subset_lengths
                summary["first_subset_length"] = first_subset_length
                if first_subset_length in (10, 11):
                    summary["format"] = "inline_room_names"
                elif first_subset_length == 8:
                    summary["format"] = "room_ids_need_getMapSubSet"
                else:
                    summary["format"] = "unknown_room_subset_format"
                    summary["subsets_preview"] = subsets[:10]
                summary["subset_ids"] = [
                    int(subset[0])
                    for subset in subsets
                    if isinstance(subset, list) and subset
                ]
                if os.environ.get("ECOVACS_INSPECT_RAW_MAP") == "1":
                    summary["subsets_preview"] = subsets[:10]

    return {key: value for key, value in summary.items() if value is not None}


async def main() -> None:
    """Inspect map-related events for one configured account device."""
    async with aiohttp.ClientSession() as session:
        logging.basicConfig(level=logging.WARNING)
        rest = create_rest_config(
            session=session,
            device_id=md5(str(time.time())),
            alpha_2_country=os.environ["ECOVACS_COUNTRY"],
            auth_domain=os.environ.get("ECOVACS_AUTH_DOMAIN", AUTH_DOMAIN_ECOVACS),
        )
        authenticator = Authenticator(
            rest,
            os.environ["ECOVACS_USERNAME"],
            md5(os.environ["ECOVACS_PASSWORD"]),
        )

        device_info = _select_device(
            (await ApiClient(authenticator).get_devices()).mqtt
        )
        device = Device(device_info, authenticator)
        await GetCachedMapInfo().execute(
            authenticator, device.device_info, device.events
        )

        cached_maps = device.events.get_last_event(CachedMapInfoEvent)
        active_map = (
            next((map_info for map_info in cached_maps.maps if map_info.using), None)
            if cached_maps
            else None
        )

        room_set_result = None
        if active_map and device.capabilities.map:
            room_set_result = await device.capabilities.map.set.execute(
                active_map.id, MapSetType.ROOMS
            ).execute(authenticator, device.device_info, device.events)

        await asyncio.sleep(0.1)

        rooms = device.events.get_last_event(RoomsEvent)
        map_info = device.events.get_last_event(MapInfoEvent)
        await device.teardown()

    output: dict[str, object] = {
        "device": {
            "class": device_info.api["class"],
            "company": device_info.api["company"],
            "name": device_info.api.get("name"),
            "nick": device_info.api.get("nick"),
        },
        "cached_maps": [
            _map_summary(map_info)
            for map_info in sorted(
                cached_maps.maps if cached_maps else set(),
                key=lambda map_info: (not map_info.using, map_info.id),
            )
        ],
        "active_map": _map_summary(active_map) if active_map else None,
        "rooms_event": _summarize_rooms_event(rooms),
        "map_info_v2": (
            {
                "map_id": map_info.map_id,
                "info_length": len(map_info.info),
            }
            if map_info
            else None
        ),
    }
    if room_set_result is not None:
        output["rooms_map_set_response"] = _summarize_map_set_response(room_set_result)

    sys.stdout.write(orjson.dumps(output, option=orjson.OPT_INDENT_2).decode())
    sys.stdout.write("\n")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
