"""List account devices without printing tokens or full device identifiers."""

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
from deebot_client.const import AUTH_DOMAIN_ECOVACS
from deebot_client.util import md5

if TYPE_CHECKING:
    from deebot_client.models import ApiDeviceInfo


def _redacted_device(device: ApiDeviceInfo) -> dict[str, Any]:
    return {
        "class": device.get("class"),
        "company": device.get("company"),
        "deviceName": device.get("deviceName"),
        "name": device.get("name"),
        "nick": device.get("nick"),
    }


async def main() -> None:
    """List supported and unsupported devices for the configured account."""
    async with aiohttp.ClientSession() as session:
        logging.basicConfig(level=logging.INFO)
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
        api_client = ApiClient(authenticator)
        devices = await api_client.get_devices()

        output = {
            "mqtt": [_redacted_device(device.api) for device in devices.mqtt],
            "xmpp": [_redacted_device(device) for device in devices.xmpp],
            "not_supported": [
                _redacted_device(device) for device in devices.not_supported
            ],
        }
        sys.stdout.write(orjson.dumps(output, option=orjson.OPT_INDENT_2).decode())
        sys.stdout.write("\n")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
