#!/usr/bin/env python3
"""Local integration test script for GOAT mower CleanMower command.

Usage (credentials via env vars - never in shell history):
    ECOVACS_USER=you@email.com ECOVACS_PASS=yourpass ECOVACS_COUNTRY=US \
        uv run python scripts/test_mower.py

Optional flags:
    --start          Actually send CleanMower(START), wait, then return to dock
    --dock-after N   Seconds between START and return-to-dock (default 30)
    --class XXXXX    Override device class to target (default: any mower)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import secrets
import sys
from datetime import UTC, datetime

from aiohttp import ClientSession

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.clean import CleanMower, GetCleanInfo
from deebot_client.device import Device
from deebot_client.events import StateEvent
from deebot_client.models import CleanAction
from deebot_client.mqtt_client import MqttClient, create_mqtt_config
from deebot_client.util import md5

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
# Quiet noisy libraries
for _noisy in ("aiohttp", "aiomqtt", "charset_normalizer"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

_LOGGER = logging.getLogger("test_mower")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", action="store_true", help="Send CleanMower(START), wait, then return to dock")
    p.add_argument("--dock-after", type=int, default=30, metavar="N", help="Seconds to mow before returning to dock (default 30)")
    p.add_argument("--class", dest="device_class", default=None, metavar="CLASS", help="Target device class (default: first mower found)")
    return p.parse_args()


async def main() -> None:
    args = _parse_args()

    username = os.environ.get("ECOVACS_USER", "")
    password = os.environ.get("ECOVACS_PASS", "")
    country = os.environ.get("ECOVACS_COUNTRY", "US")

    if not username or not password:
        _LOGGER.error("Set ECOVACS_USER and ECOVACS_PASS environment variables.")
        sys.exit(1)

    device_id = secrets.token_hex(8)
    _LOGGER.info("Using ephemeral device_id=%s country=%s", device_id, country)

    async with ClientSession() as session:
        rest_config = create_rest_config(
            session,
            device_id=device_id,
            alpha_2_country=country,
        )

        authenticator = Authenticator(rest_config, username, md5(password))
        try:
            creds = await authenticator.authenticate()
            _LOGGER.info("Authenticated as user_id=%s", creds.user_id)
        except Exception:
            _LOGGER.exception("Authentication failed")
            sys.exit(1)

        api_client = ApiClient(authenticator)
        devices_result = await api_client.get_devices()

        _LOGGER.info(
            "Discovered %d MQTT device(s), %d unsupported",
            len(devices_result.mqtt),
            len(devices_result.not_supported),
        )

        target = None
        for dev in devices_result.mqtt:
            cls = dev.api["class"]
            _LOGGER.info("  Device: name=%s class=%s did=%s", dev.api.get("name"), cls, dev.api["did"])
            if args.device_class:
                if cls == args.device_class:
                    target = dev
            elif dev.static.capabilities.device_type.name == "MOWER":
                target = dev

        if target is None:
            _LOGGER.error("No matching mower found. Use --class to specify a device class.")
            sys.exit(1)

        _LOGGER.info(
            "Target mower: name=%s class=%s did=%s",
            target.api.get("name"), target.api["class"], target.api["did"],
        )

        mqtt_config = create_mqtt_config(device_id=device_id, country=country)
        mqtt_client = MqttClient(mqtt_config, authenticator)

        device = Device(target, authenticator)

        received_events: list[tuple[datetime, StateEvent]] = []

        async def on_state(event: StateEvent) -> None:
            ts = datetime.now(tz=UTC)
            received_events.append((ts, event))
            _LOGGER.info("[STATE EVENT] %s  state=%s", ts.isoformat(), event.state.name)

        device.events.subscribe(StateEvent, on_state)

        await device.initialize(mqtt_client)
        _LOGGER.info("Subscribed to MQTT. Polling current state via GetCleanInfo...")

        # Poll current state
        response = await device.execute_command(GetCleanInfo())
        _LOGGER.info("GetCleanInfo response: %s", response)

        if not args.start:
            _LOGGER.info("--start not set. Waiting 5 s for any unsolicited events then exiting.")
            await asyncio.sleep(5)
        else:
            _LOGGER.info("Sending CleanMower(START)...")
            start_resp = await device.execute_command(CleanMower(CleanAction.START))
            _LOGGER.info("START response: %s", start_resp)

            _LOGGER.info("Mowing for %d seconds, then returning to dock...", args.dock_after)
            await asyncio.sleep(args.dock_after)

            _LOGGER.info("Sending Charge() (return to dock)...")
            dock_resp = await device.execute_command(Charge())
            _LOGGER.info("DOCK response: %s", dock_resp)

            # Wait for RETURNING → DOCKED state transitions to arrive
            await asyncio.sleep(5)

        await device.teardown()
        await mqtt_client.disconnect()
        await authenticator.teardown()

    _LOGGER.info("Done. Total StateEvents received: %d", len(received_events))
    for ts, ev in received_events:
        print(f"  {ts.isoformat()}  {ev.state.name}")


if __name__ == "__main__":
    asyncio.run(main())
