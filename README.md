# Client Library for Deebot devices (Vacuums)

[![PyPI - Downloads](https://img.shields.io/pypi/dw/deebot-client?style=for-the-badge)](https://pypi.org/project/deebot-client)
<a href="https://www.buymeacoffee.com/edenhaus" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>

## IMPORTANT: Contribution only

This project is maintained in our spare time. Please be patient and respectful.

It's not related to Ecovacs or Deebot and we don't get any support from them.

As all is reverse engineered it might take some time to add new features and we can't guarantee that all features will be added.

Unfortunately some people think we are paid to do this and get angry if things don't work as they expect.
**As result of this, we decided that this project is in a contribution only mode.**

This means, if you want something to be supported/added, you have to provide a fix yourself, wait for someone else to fix it or pay someone to do it.
Members will still review and help on pull requests.

## Installation

If you have a recent version of Python 3, you should be able to
do `pip install deebot-client` to get the most recently released version of
this.

## Usage

To get started, you'll need to have already set up an EcoVacs account
using your smartphone.

You are welcome to try using this as a python library for other efforts.
A simple usage might go something like this:

```python
import aiohttp
import asyncio
import logging
import time

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.commands.json.clean import Clean, CleanAction
from deebot_client.events import BatteryEvent
from deebot_client.mqtt_client import MqttClient, create_mqtt_config
from deebot_client.util import md5
from deebot_client.device import Device

device_id = md5(str(time.time()))
account_id = "your email or phonenumber (cn)"
password_hash = md5("yourPassword")
country = "DE"


async def main():
    async with aiohttp.ClientSession() as session:
        logging.basicConfig(level=logging.DEBUG)
        rest_config = create_rest_config(
            session, device_id=device_id, alpha_2_country=country
        )

        authenticator = Authenticator(rest_config, account_id, password_hash)
        api_client = ApiClient(authenticator)

        devices_ = await api_client.get_devices()

        bot = Device(devices_.mqtt[0], authenticator)

        mqtt_config = create_mqtt_config(device_id=device_id, country=country)
        mqtt = MqttClient(mqtt_config, authenticator)
        await bot.initialize(mqtt)

        async def on_battery(event: BatteryEvent):
            # Do stuff on battery event
            if event.value == 100:
                # Battery full
                pass

        # Subscribe for events (more events available)
        bot.events.subscribe(BatteryEvent, on_battery)

        # Execute commands
        await bot.execute_command(Clean(CleanAction.START))
        await asyncio.sleep(900)  # Wait for...
        await bot.execute_command(Charge())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
```

A more advanced example can be found [here](https://github.com/And3rsL/Deebot-for-Home-Assistant).

### DEEBOT Y1 Pro (cqyi87)

Drive cleaning through the clean action capability, not the legacy `Clean` command:

```python
from deebot_client.models import CleanAction, CleanMode

await bot.execute_command(bot.capabilities.clean.action.command(CleanAction.START))
await bot.execute_command(bot.capabilities.clean.action.command(CleanAction.PAUSE))
await bot.execute_command(bot.capabilities.clean.action.command(CleanAction.RESUME))
await bot.execute_command(bot.capabilities.clean.action.command(CleanAction.STOP))

# Area cleaning (spot / custom zone):
await bot.execute_command(
    bot.capabilities.clean.action.area(CleanMode.SPOT_AREA, [1, 2])
)
await bot.execute_command(
    bot.capabilities.clean.action.area(CleanMode.CUSTOM_AREA, [x1, y1, x2, y2])
)
```

`STOP` ends the task and returns to dock. `PAUSE` halts in place.
Use the room IDs from `RoomsEvent` for room cleaning. Zone and map-edit capability coordinates are in millimeters and must align to 10 mm; the native protocol uses centimeters. Area cleaning supports one repetition per command.

Native settings are exposed through canonical capabilities:

- `bot.capabilities.settings.child_lock`
- `bot.capabilities.settings.carpet_auto_fan_boost`
- `bot.capabilities.clean.continuous`
- `bot.capabilities.settings.do_not_disturb`
- `bot.capabilities.settings.volume` (range 0..10)

Native map capabilities are exposed through canonical map capabilities:

- `bot.capabilities.map.cached_info`: Saved map catalog query via opcode 30001 (`mapInfos`).
- `bot.capabilities.map.info`: Read-only map inspection via opcode 30001 (`mapData`, `areas`, `pos`).
- `bot.capabilities.map.map_switch`: Active navigation map switcher via opcode 30004 (`mapSwitch`).
- `bot.capabilities.map.edit`: Native map edits with millimeter-adapted API:
  - `add_virtual_wall(map_id, [x1, y1, x2, y2])` / `delete_virtual_wall(map_id, wall_id)` (opcode 50001)
  - `add_no_mop_zone(map_id, [x1, y1, ...])` / `delete_no_mop_zone(map_id, zone_id)` (opcode 50001)
  - `split_room(map_id, room_id, [x1, y1, x2, y2])` (opcode 50005)
  - `merge_rooms(map_id, [room_id_1, room_id_2])` (opcode 50007)
  - `rename_room(map_id, room_id, name)` (opcode 50009)
- `bot.capabilities.map.position`: Real-time robot and charger pose telemetry (opcode 30000 / 30001).
- `bot.capabilities.map.rooms`: Dynamic room metadata and center coordinates (opcode 30000 / 30001).
- `bot.capabilities.map.trace`: `NativeTraceEvent` trajectory stream with cursor rewind deduplication (opcode 30000 / 30001).
- Native whole-raster LZ4 background decoding and SVG rendering integrated via Rust backend.
- `bot.map.select_map(map_id)`: inspect saved map without navigation switch; stale pushes for other maps are dropped.
- `await bot.map.fetch_map(map_id)`: select plus read-only 30001 fetch of raster, traces, overlays for that map.
- `bot.map.refresh()`: refreshes selected inspected map when set, else catalog.
- `PositionsEvent`, `RoomsEvent`, `NativeTraceEvent`, and overlay subset events carry `map_id`; consumers showing rooms filter on the selected id.

Standalone position, room, and trace subscriptions fetch the catalog and then query the active map. Successful MQTT map edits refresh the edited map, including inactive maps. Legacy models retain their original trace events and integer-keyed map-subset interface.

Station actions and cleaning-duration totals are not yet exposed by this profile.

Firmware may redact `deviceInfo.ssid`/`rssi` (returns `xxx`), leaving network diagnostics unknown; parser skips non-numeric RSSI and emits no fabricated event.

### Note for Windows users

This library cannot be used out of the box with Windows due a limitation in the requirement `aiomqtt`.
More information and a workaround can be found [here](https://github.com/sbtinstruments/aiomqtt#note-for-windows-users)

## Thanks

My heartfelt thanks to:

- [deebotozmo](https://github.com/And3rsL/Deebotozmo), After all, this is a debotozmo fork :)
- [sucks](https://github.com/wpietri/sucks), deebotozmo was forked from it :)
- [xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html), a great library for examining XMPP traffic flows (
  yes, your vacuum speaks Jabber!),
- [mitmproxy](https://mitmproxy.org/), a fantastic tool for analyzing HTTPS,
- [click](http://click.pocoo.org/), a wonderfully complete and thoughtful library for making Python command-line
  interfaces,
- [requests](http://docs.python-requests.org/en/master/), a polished Python library for HTTP requests,
- [Decompilers online](http://www.javadecompilers.com/apk), which was very helpful in figuring out what the Android app
  was up to,
- Albert Louw, who was kind enough to post code
  from [his own experiments](https://community.smartthings.com/t/ecovacs-deebot-n79/93410/33)
  with his device, and
- All the users who have given useful feedback and contributed code!
