from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp


def derive_ngiot_base_url(mqs_host: str) -> str:
    parsed = urlparse(mqs_host)
    host = parsed.netloc or parsed.path
    host = host.strip().rstrip("/")
    if not host:
        raise ValueError(f'Could not derive NGIOT base URL from mqs host "{mqs_host}"')
    if host.startswith("api-base."):
        return f"https://{host}"
    if host.startswith("api-ngiot."):
        return f"https://api-base.{host.split('.', 1)[1]}"
    if "." in host:
        return f"https://api-base.{host.split('.', 1)[1]}"
    raise ValueError(f'Could not derive NGIOT base URL from mqs host "{mqs_host}"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quick NGIOT probe for Ecovacs eco-ng devices")
    parser.add_argument("--repo", required=True, help="Repo root containing deebot_client/")
    parser.add_argument("--country", required=True, help="2-letter country code, e.g. AU")
    parser.add_argument("--account", required=True, help="Ecovacs account email")
    parser.add_argument("--password", required=True, help="Ecovacs account password")
    parser.add_argument("--class", dest="class_id", default="eyfj07", help="Device class id")
    parser.add_argument("--did", help="Specific device id if multiple devices share the same class")
    parser.add_argument("--list-devices", action="store_true", help="List eco-ng devices and exit")
    parser.add_argument("--get-info", action="store_true", help="Read a broad 10001 status payload")
    parser.add_argument("--status", action="store_true", help="Read a smaller status payload")
    parser.add_argument("--totals", action="store_true", help="Read total stats payload")
    parser.add_argument(
        "--action",
        choices=["start", "pause", "resume", "return", "cancel-return", "locate"],
        help="Run a captured control action",
    )
    parser.add_argument("--area", help="Comma-separated room ids for area clean, e.g. 1 or 1,2")
    parser.add_argument("--fan-mode", choices=["quiet", "auto", "strong", "max"], help="Set fan mode")
    parser.add_argument("--volume", type=int, help="Set volume 0..10")
    parser.add_argument("--raw-apn", help="Send a raw APN")
    parser.add_argument("--raw-json", help='Send raw body data JSON, e.g. \'{"seek":true}\'')
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / "deebot_client").is_dir():
        print(f"Invalid --repo: {repo} does not contain deebot_client/", file=sys.stderr)
        return 2

    sys.path.insert(0, str(repo))

    from deebot_client.api_client import ApiClient
    from deebot_client.authentication import Authenticator, create_rest_config
    from deebot_client.util import md5

    device_id = md5(str(time.time()))
    password_hash = md5(args.password)

    async with aiohttp.ClientSession() as session:
        rest_config = create_rest_config(
            session,
            device_id=device_id,
            alpha_2_country=args.country,
        )
        authenticator = Authenticator(rest_config, args.account, password_hash)
        api_client = ApiClient(authenticator)

        devices = await api_client.get_devices()

        eco_ng_devices: list[dict[str, Any]] = []
        for dev in devices.mqtt:
            eco_ng_devices.append(dev.api)
        for dev in devices.not_supported:
            if dev.get("company") == "eco-ng":
                eco_ng_devices.append(dev)

        if args.list_devices:
            print(
                json.dumps(
                    [
                        {
                            "did": d.get("did"),
                            "class": d.get("class"),
                            "nick": d.get("nick"),
                            "resource": d.get("resource"),
                            "company": d.get("company"),
                            "mqs": (d.get("service") or {}).get("mqs"),
                        }
                        for d in eco_ng_devices
                    ],
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        target: dict[str, Any] | None = None
        for dev in eco_ng_devices:
            if args.did and dev.get("did") == args.did:
                target = dev
                break
            if not args.did and dev.get("class") == args.class_id:
                target = dev
                break

        if target is None:
            print(
                f'No eco-ng device found for class "{args.class_id}"'
                + (f' and did "{args.did}"' if args.did else ""),
                file=sys.stderr,
            )
            return 3

        service = target.get("service") or {}
        mqs_host = service.get("mqs")
        if not isinstance(mqs_host, str) or not mqs_host:
            print(f'Device is missing service.mqs: {json.dumps(target, indent=2)}', file=sys.stderr)
            return 4

        ngiot_base_url = derive_ngiot_base_url(mqs_host)
        authenticator.attach_ngiot(
            base_url=ngiot_base_url,
            timezone_name="Australia/Brisbane",
            timezone_offset_minutes=600,
        )

        ngiot = authenticator.ngiot_client
        if ngiot is None:
            print("Failed to attach NGIOT client", file=sys.stderr)
            return 5

        async def run_request(apn: str, body_data: dict[str, Any]) -> None:
            response = await ngiot.request(target, apn=apn, body_data=body_data)
            print(json.dumps(response, indent=2, sort_keys=True))

        did = target.get("did")
        class_id = target.get("class")
        nick = target.get("nick")
        print(f"Using device did={did} class={class_id} nick={nick}", file=sys.stderr)

        if args.get_info:
            await run_request(
                "10001",
                {
                    "fields": [
                        "stationType",
                        "stationStatus",
                        "cleanValues",
                        "chargeStatus",
                        "pauseSwitch",
                        "battery",
                        "disturbSwitch",
                        "disturbTimeSet",
                        "mopState",
                        "workMode",
                        "breakCleanStatus",
                        "fanMode",
                        "waterMode",
                        "cleanCount",
                        "error",
                        "consumables",
                        "newMapReport",
                        "expandedMapReport",
                        "cleanLogReport",
                        "deviceInfo",
                        "childLock",
                        "isEurope",
                        "cleanTime",
                        "cleanArea",
                        "silentOtaSwitch",
                        "nextSchedule",
                        "dormant",
                        "relocateSwitch",
                        "unitSet",
                        "otaData",
                        "voiceData",
                        "timeZone",
                    ]
                },
            )

        if args.status:
            await run_request(
                "10001",
                {
                    "fields": [
                        "chargeStatus",
                        "pauseSwitch",
                        "workMode",
                        "error",
                        "battery",
                        "fanMode",
                        "waterMode",
                        "cleanArea",
                        "cleanTime",
                        "cleanCount",
                    ]
                },
            )

        if args.totals:
            await run_request(
                "10001",
                {
                    "fields": [
                        "cleanAreaTotal",
                        "cleanCountTotal",
                        "cleanTimeTotal",
                    ]
                },
            )

        if args.action == "start":
            await run_request("40001", {"cleanSwitch": True, "cleanMode": "smart"})
        elif args.action == "pause":
            await run_request("40009", {"pauseSwitch": True})
        elif args.action == "resume":
            await run_request("40011", {"pauseSwitch": False})
        elif args.action == "return":
            await run_request("40013", {"chargeSwitch": True})
        elif args.action == "cancel-return":
            await run_request("40015", {"chargeSwitch": False})
        elif args.action == "locate":
            await run_request("40019", {"seek": True})

        if args.area:
            room_ids = [int(x.strip()) for x in args.area.split(",") if x.strip()]
            await run_request(
                "40007",
                {
                    "cleanSwitch": True,
                    "cleanMode": "area",
                    "cleanValues": room_ids,
                },
            )

        if args.fan_mode:
            await run_request("50011", {"fanMode": args.fan_mode})

        if args.volume is not None:
            if not 0 <= args.volume <= 10:
                print("--volume must be between 0 and 10", file=sys.stderr)
                return 6
            await run_request("50023", {"volume": args.volume})

        if args.raw_apn:
            body_data = json.loads(args.raw_json or "{}")
            if not isinstance(body_data, dict):
                print("--raw-json must decode to a JSON object", file=sys.stderr)
                return 7
            await run_request(args.raw_apn, body_data)

        await authenticator.teardown()
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
