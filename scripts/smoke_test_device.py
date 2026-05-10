"""Run read-only capability commands for one device."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import os
import sys
import time
from typing import TYPE_CHECKING

import aiohttp
import orjson

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.const import AUTH_DOMAIN_ECOVACS
from deebot_client.device import Device
from deebot_client.events import Event
from deebot_client.util import md5

if TYPE_CHECKING:
    from collections.abc import Iterable

    from deebot_client.command import Command, DeviceCommandResult
    from deebot_client.models import DeviceInfo


@dataclass(frozen=True)
class SmokeResult:
    """Result of a single smoke-test command."""

    command: str
    device_reached: bool
    response: dict[str, object]


def _event_classes() -> Iterable[type[Event]]:
    seen: set[type[Event]] = set()
    todo = list(Event.__subclasses__())
    while todo:
        event_type = todo.pop()
        if event_type in seen:
            continue
        seen.add(event_type)
        yield event_type
        todo.extend(event_type.__subclasses__())


def _refresh_commands(device: Device) -> list[Command]:
    commands: dict[tuple[str, str], Command] = {}
    for event_type in _event_classes():
        for command in device.capabilities.get_refresh_commands(event_type):
            commands[(command.NAME, repr(command))] = command
    return sorted(commands.values(), key=lambda command: (command.NAME, repr(command)))


def _summarize_response(result: DeviceCommandResult) -> dict[str, object]:
    response = result.raw_response
    payload = response.get("resp", response)
    body = payload.get("body") if isinstance(payload, dict) else None
    summary: dict[str, object] = {
        "ret": response.get("ret"),
        "errno": response.get("errno"),
        "error": response.get("error"),
    }
    if isinstance(body, dict):
        summary["body_code"] = body.get("code")
        summary["body_msg"] = body.get("msg")
        data = body.get("data")
        if isinstance(data, dict):
            summary["body_data_keys"] = sorted(data)
        elif isinstance(data, list):
            summary["body_data_count"] = len(data)
            data_types = sorted(
                {
                    str(entry["type"])
                    for entry in data
                    if isinstance(entry, dict) and "type" in entry
                }
            )
            if data_types:
                summary["body_data_types"] = data_types
    return {key: value for key, value in summary.items() if value is not None}


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


async def main() -> None:
    """Run smoke-test commands for one configured account device."""
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
        results: list[SmokeResult] = []

        for command in _refresh_commands(device):
            result = await command.execute(
                authenticator, device.device_info, device.events
            )
            results.append(
                SmokeResult(
                    command=repr(command),
                    device_reached=result.device_reached,
                    response=_summarize_response(result),
                )
            )

        await device.teardown()

    sys.stdout.write(
        orjson.dumps(
            {
                "device": {
                    "class": device_info.api["class"],
                    "company": device_info.api["company"],
                    "name": device_info.api.get("name"),
                    "nick": device_info.api.get("nick"),
                },
                "commands": [result.__dict__ for result in results],
            },
            option=orjson.OPT_INDENT_2,
        ).decode()
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
