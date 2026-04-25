from __future__ import annotations

from deebot_client.commands.ngiot import COMMANDS
from deebot_client.commands.ngiot.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.ngiot.error import GetError
from deebot_client.commands.ngiot.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.ngiot.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.ngiot.network import GetNetInfo
from deebot_client.commands.ngiot.play_sound import PlaySound
from deebot_client.commands.ngiot.stats import GetReportStats, GetStats, GetTotalStats
from deebot_client.commands.ngiot.volume import GetVolume, SetVolume


def test_ngiot_command_registry_includes_non_map_commands() -> None:
    expected = {
        "getChildLock": GetChildLock,
        "setChildLock": SetChildLock,
        "getError": GetError,
        "getSpeed": GetFanSpeed,
        "setSpeed": SetFanSpeed,
        "getLifeSpan": GetLifeSpan,
        "resetLifeSpan": ResetLifeSpan,
        "getNetInfo": GetNetInfo,
        "seek": PlaySound,
        "getStats": GetStats,
        "getReportStats": GetReportStats,
        "getTotalStats": GetTotalStats,
        "getVolume": GetVolume,
        "setVolume": SetVolume,
    }

    for name, command in expected.items():
        assert COMMANDS[name] is command
