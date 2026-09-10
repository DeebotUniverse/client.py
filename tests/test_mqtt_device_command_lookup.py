from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.const import DataType
from deebot_client.mqtt_client import MqttClient, MqttConfiguration, SubscriberInfo

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import DeviceInfo


def test_p2p_command_lookup_is_device_specific(
    authenticator: Authenticator,
    device_info: DeviceInfo,
    event_bus: EventBus,
) -> None:
    """Test P2P command lookup uses the device-specific command."""

    class AlternativeSetVolume(SetVolume):
        """Alternative set volume command using the same command name."""

    class NonP2PSetVolume(GetVolume):
        """Non-P2P command using the same command name."""

        NAME = SetVolume.NAME

    client = MqttClient(
        MqttConfiguration(
            hostname="localhost",
            port=1883,
            ssl_context=None,
            device_id="test",
        ),
        authenticator,
    )

    volume = device_info.static.capabilities.settings.volume
    assert volume is not None

    client._subscriptions[device_info.api["did"]] = SubscriberInfo(
        device_info=device_info,
        events=event_bus,
        callback=lambda _name, _payload: None,
    )

    assert (
        client._get_p2p_command_type(
            SetVolume.NAME,
            DataType.JSON,
            device_info.api["did"],
        )
        is SetVolume
    )

    alternative_capabilities = replace(
        device_info.static.capabilities,
        settings=replace(
            device_info.static.capabilities.settings,
            volume=replace(
                volume,
                set=AlternativeSetVolume,
            ),
        ),
    )
    alternative_device_info = replace(
        device_info,
        static=replace(
            device_info.static,
            capabilities=alternative_capabilities,
        ),
    )

    client._subscriptions[device_info.api["did"]] = SubscriberInfo(
        device_info=alternative_device_info,
        events=event_bus,
        callback=lambda _name, _payload: None,
    )

    assert (
        client._get_p2p_command_type(
            SetVolume.NAME,
            DataType.JSON,
            device_info.api["did"],
        )
        is AlternativeSetVolume
    )

    non_p2p_capabilities = replace(
        device_info.static.capabilities,
        settings=replace(
            device_info.static.capabilities.settings,
            volume=replace(
                volume,
                set=NonP2PSetVolume,
            ),
        ),
    )
    non_p2p_device_info = replace(
        device_info,
        static=replace(
            device_info.static,
            capabilities=non_p2p_capabilities,
        ),
    )

    client._subscriptions[device_info.api["did"]] = SubscriberInfo(
        device_info=non_p2p_device_info,
        events=event_bus,
        callback=lambda _name, _payload: None,
    )

    assert (
        client._get_p2p_command_type(
            SetVolume.NAME,
            DataType.JSON,
            device_info.api["did"],
        )
        is None
    )

    assert (
        client._get_p2p_command_type(
            SetVolume.NAME,
            DataType.JSON,
            "unknown-device",
        )
        is SetVolume
    )

    no_volume_capabilities = replace(
        device_info.static.capabilities,
        settings=replace(
            device_info.static.capabilities.settings,
            volume=None,
        ),
    )
    no_volume_device_info = replace(
        device_info,
        static=replace(
            device_info.static,
            capabilities=no_volume_capabilities,
        ),
    )
    client._subscriptions[device_info.api["did"]] = SubscriberInfo(
        device_info=no_volume_device_info,
        events=event_bus,
        callback=lambda _name, _payload: None,
    )

    assert (
        client._get_p2p_command_type(
            SetVolume.NAME,
            DataType.JSON,
            device_info.api["did"],
        )
        is SetVolume
    )
