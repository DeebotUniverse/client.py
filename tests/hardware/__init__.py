from collections.abc import Mapping

from deebot_client.hardware.device_capabilities import DeviceCapabilities


def verify_sorted_devices(devices: Mapping[str, DeviceCapabilities]) -> None:
    sorted_keys = sorted(devices.keys())
    assert sorted_keys == list(
        devices.keys()
    ), f"Devices expected to sort like {sorted_keys}"
    for device in devices.values():
        verify_get_refresh_commands(device)


def verify_get_refresh_commands(device_capabilites: DeviceCapabilities) -> None:
    for event in device_capabilites.events.keys():
        device_capabilites.get_refresh_commands(event)
